## SAJ MODBUS TCP

Home assistant Custom Component for reading data from SAJ inverters through modbus TCP. Implements SAJ Inverter registers from https://www.solartoday.nl/wp-content/uploads/saj-plus-series-inverter-modbus-protocal.pdf .

Based on home-assistant-solaredge-modbus from binsentsu https://github.com/binsentsu/home-assistant-solaredge-modbus

### Features

- Installation through Config Flow UI.
- Separate sensor per register
- Auto applies scaling factor
- Configurable polling interval
- All modbus registers are read within 1 read cycle for data consistency between sensors.


### Configuration
Go to the integrations page in your configuration and click on new integration -> SAJ Modbus
