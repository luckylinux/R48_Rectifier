import rectifier
import random
import pprint
import time

if __name__ == "__main__":
    # Setup class
    Charger = Rectifier(channel = 'can-grid-00')

    # Infinite Loop
    while True:
        # Generate Random Voltage between 48VDC and 56VDC
        random_voltage = random.uniform(48 , 56)

        # Generate Random Current Limit between 5.5ADC and 50ADC
        random_current_limit = random.uniform(5.5 , 50)

	# Set values
        Charger.set_voltage(voltage = random_voltage , fixed = False)
        Charger.set_current_value(current = random_current_limit , fixed = False)

        # Read values
        pprint(Charger.get_readout())

        # Wait 120 seconds
        time.sleep(120)
