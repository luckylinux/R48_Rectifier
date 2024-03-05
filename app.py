from rectifier import Rectifier
import random
import pprint
import time

if __name__ == "__main__":
    # Setup class
    Charger = Rectifier(interface = 'can-grid-00')

    # Set Initial Values
    Charger.set_output_voltage(voltage = 51 , fixed = False)
    Charger.set_output_current_limit_value(current = 50 , fixed = False)

    # Run class
    Charger.run(debug=True)

    # Infinite Loop
    while True:
        # Generate Random Voltage between 48VDC and 56VDC
        random_voltage = random.uniform(48 , 56)

        # Generate Random Current Limit between 5.5ADC and 50ADC
        random_current_limit = random.uniform(5.5 , 50)

	    # Set values
        Charger.set_output_voltage(voltage = random_voltage , fixed = False)
        Charger.set_output_current_limit_value(current = random_current_limit , fixed = False)

        # Read values
        pprint.pprint(Charger.get_readout())

        # Wait
        time.sleep(5)
