# Import Core Libraries
import sys
import struct
import subprocess
import time
import argparse

# Suppress echo
import contextlib

# Import can (python-can) Libraries
import can

# Encapsulate everything within a class
# Allows the usage with different ratings of Rectifiers, by allowing the user to override OUTPUT_CURRENT_RATED_VALUE and OUTPUT_CURRENT_MIN
# This way, it can be used with Emerson/Vertiv R48-3000e3 as well as Emerson/Vertiv R48-2000e3 and probably Emerson/Vertiv R48-5800e3.
# If the same structure of data is also used in the case of Emerson/Vertiv R24-3000 etc, then the parameters OUTPUT_VOLTAGE_MIN and OUTPUT_VOLTAGE_MAX can also be tweaked.
# Arbitration ID could also be modified by an external application, if needed.

# Declare class
class Rectifier:
    # CAN stuff
    ARBITRATION_ID = 0x0607FF83 # or 06080783 ?
    ARBITRATION_ID_READ = 0x06000783
    BITRATE = 125000

    # individual properties to read out, data: 0x01, 0xF0, 0x00, p, 0x00, 0x00, 0x00, 0x00 with p:
    # 01 : output voltage
    # 02 : output current
    # 03 : output current limit
    # 04 : temperature in C
    # 05 : supply voltage
    READ_COMMANDS = [0x01, 0x02, 0x03, 0x04, 0x05]

    # Reads all of the above and a few more at once
    READ_ALL = [0x00, 0xF0, 0x00, 0x80, 0x46, 0xA5, 0x34, 0x00] 

    # 62.5A is the nominal current of Emerson/Vertiv R48-3000e and corresponds to 121%
    OUTPUT_CURRENT_RATED_VALUE = 62.5
    OUTPUT_CURRENT_RATED_PERCENTAGE_MIN = 10
    OUTPUT_CURRENT_RATED_PERCENTAGE_MAX = 121
    OUTPUT_CURRENT_RATED_PERCENTAGE = 121
    OUTPUT_VOLTAGE_MIN = 41.0
    OUTPUT_VOLTAGE_MAX = 58.5
    OUTPUT_CURRENT_MIN = 5.5 # 10%, rounded up to nearest 0.5A
    OUTPUT_CURRENT_MAX = OUTPUT_CURRENT_RATED_VALUE

    # Interface Property
    Interface

    # Store Readout
    Readout

    # Store Settings
    #Settings

    # Class Constructor
    def __init__(self , channel):
        # Store Interface within Object
        self.Interface = channel

        # Initialise Readout Storage
        self.Readout = namedtuple('Readout', ['Output_Voltage', 'Output_Current_Value' , 'Output_Current_Limit' , 'Temperature' , 'Input_Voltage'])

        # Initialise Settings Storage
        #self.Settings

        # Do nothing for now
        #pass

    # Needs root/sudo access, or configure this part on the OS
    # Or use the setns function as sudo/root and assign this to the user namespace of the Docker/Podman Container
    # See https://github.com/luckylinux/solar-charger-emerson?tab=readme-ov-file#rootless-podman--docker
    def config(channel):
        # Configure CAN Interface
        subprocess.call(['ip', 'link', 'set', 'down', channel])
        subprocess.call(['ip', 'link', 'set', channel, 'type', 'can', 'bitrate', str(BITRATE), 'restart-ms', '1500'])
        subprocess.call(['ip', 'link', 'set', 'up', channel])

    # To convert floating point units to 4 bytes in a bytearray
    def float_to_bytearray(f):
        value = hex(struct.unpack('<I', struct.pack('<f', f))[0])
        return bytearray.fromhex(value.lstrip('0x').rstrip('L'))

    # Get the bus and send data to the specified CAN bus
    def send_can_message(channel, data):
        try:
            with can.interface.Bus(bustype='socketcan', channel=channel, bitrate=BITRATE) as bus:
                msg = can.Message(arbitration_id=ARBITRATION_ID, data=data, is_extended_id=True)
                bus.send(msg)
                print(f"Command sent on {bus.channel_info}")
        except can.CanError:
            print("Command NOT sent")

    # CAN message receiver
    def receive_can_message(channel , echo=true):
        try:
            with can.interface.Bus(receive_own_messages=True, bustype='socketcan', channel=channel, bitrate=BITRATE) as bus:
                #print_listener = can.Printer()
                #can.Notifier(bus, [print_listener])
                if echo is true:
                    can.Notifier(bus, [can_listener_print])
                else:
                    can.Notifier(bus, [can_listener_store])

                # Keep sending requests for all data every second 
                while True:
                    # Individually
                    #for p in READ_COMMANDS: 
                    #    data = [0x01, 0xF0, 0x00, p, 0x00, 0x00, 0x00, 0x00]
                    #    msg = can.Message(arbitration_id=ARBITRATION_ID_READ, data=data, is_extended_id=True)
                    #    bus.send(msg) 
                    #    time.sleep(0.1)

                    # All at once
                    msg = can.Message(arbitration_id=ARBITRATION_ID_READ, data=READ_ALL, is_extended_id=True)
                    bus.send(msg)
                    time.sleep(1.0)
        except can.CanError:
            print("Receive went wrong")

    # CAN receiver listener (print values to screen)
    def can_listener_print(msg):
        # Is it a response to our request
        if msg.data[0] == 0x41:
            # Convert value to float (it's the same for all)
            val = struct.unpack('>f', msg.data[4:8])[0]

            # Check what data it is
            match msg.data[3] :
                case 0x01:
                    print("Vout (VDC) : " + str(val))
                case 0x02:
                    print("Iout (IDC) : " + str(val))
                case 0x03:
                    print("Output Current Limit : " + str(val))
                case 0x04:
                    print("Temp (C) : " + str(val))
                case 0x05:
                    print("Vin (VAC) : " + str(val)) 

    # CAN receiver listener (register values within an object)
    # Not really the best approach, but how to pass optional argument "echo" to CAN.Notifier in case of another solution ? 
    def can_listener_store(msg):
        # Is it a response to our request
        if msg.data[0] == 0x41:
            # Convert value to float (it's the same for all)
            val = struct.unpack('>f', msg.data[4:8])[0]

            # Check what data it is
            match msg.data[3] :
                case 0x01:
                    self.Readout.Output_Voltage = val
                case 0x02:
                    self.Readout.Output_Current_Value = val
                case 0x03:
                    self.Readout.Output_Current_Limit = val
                case 0x04:
                    self.Readout.Temperature = val
                case 0x05:
                    self.Readout.Input_Voltage = val

    # Get all Readout
    def get_readout(channel):
        # Just call receive_can_message
        return receive_can_message(channel)

    # Get the Output Voltage Readout In VDC
    # This might be different than the set value in case the Charger is cperating in Current-Limitation 
    def get_output_voltage(channel):
        # Just return the requested field
        return self.Readout.Output_Voltage
    
    # Get the Output Current Readout in ADC
    # If this value is equal (or very close) to the Output Current Limit, the Charger is most likely operating in Current-Limitation 
    def get_output_current_value(channel):
        # Just return the requested field
        return self.Readout.Output_Current_Value

    # Get the Output Current Limit set in ADC
    # If this value is equal (or very close) to the Output Current Value, the Charger is most likely operating in Current-Limitation 
    def get_output_current_limit(channel):
        # Just return the requested field
        return self.Readout.Output_Current_Limit

    # Get the Temperature Readout of the Rectifier in °C
    def get_temperature(channel):
        # Just return the requested field
        return self.Readout.Temperature

    # Get the Input Voltage Readout in VAC
    def get_input_voltage(channel):
        # Just return the requested field
        return self.Readout.Input_Voltage

    # Set the output voltage to the new value. 
    # The 'fixed' parameter 
    #  - if True makes the change permanent ('offline command')
    #  - if False the change is temporary (30 seconds per command received, 'online command', repeat at 15 second intervals).
    # Voltage between 41.0 and 58.5V - fan will go high below 48V!
    def set_voltage(channel, voltage, fixed=False):
        if OUTPUT_VOLTAGE_MIN <= voltage <= OUTPUT_VOLTAGE_MAX:
            b = float_to_bytearray(voltage)
            p = 0x21 if not fixed else 0x24
            data = [0x03, 0xF0, 0x00, p, *b]
            send_can_message(channel, data)
        else:
            print(f"Voltage should be between {OUTPUT_VOLTAGE_MIN}V and {OUTPUT_VOLTAGE_MAX}V")

    # The output current is set in percent to the rated value of the rectifier written in the manual
    # Possible values for 'current': 10% - 121% (rated current in the datasheet = 121%)
    # The 'fixed' parameter
    #  - if True makes the change permanent ('offline command')
    #  - if False the change is temporary (30 seconds per command received, 'online command', repeat at 15 second intervals).
    def set_current_percentage(channel, current, fixed=False):
        if OUTPUT_CURRENT_RATED_PERCENTAGE_MIN <= current <= OUTPUT_CURRENT_RATED_PERCENTAGE_MAX:
            limit = current / 100
            b = float_to_bytearray(limit)
            p = 0x22 if not fixed else 0x19
            data = [0x03, 0xF0, 0x00, p, *b]
            send_can_message(channel, data)
        else:
            print(f"Current should be between {OUTPUT_CURRENT_RATED_PERCENTAGE_MIN}% and {OUTPUT_CURRENT_RATED_PERCENTAGE_MAX}%")

    # The output current is set as a value
    # Possible values for 'current': 5.5A - 62.5A
    # The 'fixed' parameter
    #  - if True makes the change permanent ('offline command')
    #  - if False the change is temporary (30 seconds per command received, 'online command', repeat at 15 second intervals).
    def set_current_value(channel, current, fixed=False): 
        if OUTPUT_CURRENT_MIN <= current <= OUTPUT_CURRENT_MAX:
            # 62.5A is the nominal current of Emerson/Vertiv R48-3000e and corresponds to 121%
            percentage = (current/OUTPUT_CURRENT_RATED_VALUE)*OUTPUT_CURRENT_RATED_PERCENTAGE
            set_current_percentage(channel , percentage, fixed)
        else:
            print(f"Current should be between {OUTPUT_CURRENT_MIN}A and {OUTPUT_CURRENT_MAX}A")

    # Time to ramp up the rectifiers output voltage to the set voltage value, and enable/disable
    def walk_in(channel, time=0, enable=False):
        if not enable:
            data = [0x03, 0xF0, 0x00, 0x32, 0x00, 0x00, 0x00, 0x00]
        else:
            data = [0x03, 0xF0, 0x00, 0x32, 0x00, 0x01, 0x00, 0x00]
            b = float_to_bytearray(time)
            data.extend(b)
        send_can_message(channel, data)

    # AC input current limit (called Diesel power limit): gives the possibility to reduce the overall power of the rectifier
    def limit_input(channel, current):
        b = float_to_bytearray(current)
        data = [0x03, 0xF0, 0x00, 0x1A, *b]
        send_can_message(channel, data)

    # Restart after overvoltage enable/disable
    def restart_overvoltage(channel, state=False):
        if not state:
            data = [0x03, 0xF0, 0x00, 0x39, 0x00, 0x00, 0x00, 0x00]
        else:
            data = [0x03, 0xF0, 0x00, 0x39, 0x00, 0x01, 0x00, 0x00]
        send_can_message(channel, data)


if __name__ == "__main__":
    # Create new Instance/Object of class Rectifier
    rectifier = Rectifier()

    # Process Command-Line Arguments
    parser = argparse.ArgumentParser(description='Set/Get Parameters from Emerson/Vertiv Rectifiers.')

    parser.add_argument('-m', '--mode', default="none",
                    help='Mode of Operation (set/get)')

    parser.add_argument('-v', '--voltage', type=float,
                    help='Output Voltage Set Point of the Charger (41.0VDC - 58.5VDV)')

    parser.add_argument('-cv', '--current_value', type=float,
                    help='Output Current Set Point of the Charger (5.5ADC - 62.5ADC)')
    parser.add_argument('-cp', '--current_percent', type=float,
                    help='Output Current Set Point of the Charger in percent (10%% - 121%%)')

    parser.add_argument('-l' , '--limit_input' , type=float,
                    help='Input Current Limit of the Charger (useful in case of e.g. small Diesel Generator, weak Grid, Grid Peak Power Shawing, ...)')

    parser.add_argument('-we' , '--walk_in_enable' , type=bool,
                    help='Enable Ramp up the Rectifier Output Voltage to the set Voltage Value (true/false)')

    parser.add_argument('-wt' , '--walk_in_time' , type=float,
                    help='Time to Ramp up the Rectifier Output Voltage to the set Voltage Value (in seconds)')

    parser.add_argument('-r' , '--restart_overvoltage' , type=bool,
                    help='Restart after Overvoltage Event (true/false)')

    parser.add_argument('-p', '--permanent', action='store_true',
                    help='Make settings permanent')

    parser.add_argument('-I', '--interface', default="can0",
                    help='Adapter Interface (can0, can1, ...)')

    parser.add_argument('-C', '--configure', action='store_true',
                    help='Configure link (bitrate, bring up interface) as well') 

    # Parse Command-Line Arguments
    args = parser.parse_args()    

    # Configure Interfaces ?
    if args.configure == True:
        rectifier.config(args.interface)    

    # Set Parameters ?
    if args.mode == "set":
        print(f"{args.permanent}")
        if args.voltage is not None:
            rectifier.set_voltage(args.interface, args.voltage, args.permanent)
        if args.current_value is not None:
            rectifier.set_current_value(args.interface, args.current_value, args.permanent)
        if args.current_percent is not None:
            rectifier.set_current_percentage(args.interface, args.current_percent, args.permanent)
        if args.limit_input is not None:
            rectifier.limit_input(args.interface , args.limit_input)
        if args.walk_in_enable is true and args.walk_in_time is not None:
            rectifier.walk_in(args.interface , args.walk_in_time , args.walk_in_enable)
    
    # Get Values ?
    elif args.mode== "get":
        rectifier.receive_can_message(args.interface , echo:=true)

    # Delete Object
    del rectifier

    # Old-style example
    #config('can0')
    #set_voltage('can0', 52.0, False)
    #set_current('can0', 10.0, False)
    #walk_in('can0', False)
    #limit_input('can0', 10.0)
    #restart_overvoltage('can0', False)
