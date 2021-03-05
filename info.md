## SAJ MODBUS TCP

Home assistant Custom Component for reading data from SAJ inverters through modbus TCP.
SAJ Inverters are also sold in The Netherlands as Zonneplan ONE inverters.
Implements SAJ Inverter registers from [`saj-plus-series-inverter-modbus-protocal.pdf`](https://github.com/wimb0/home-assistant-saj-modbus/blob/main/saj-plus-series-inverter-modbus-protocal.pdf).

Based on [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) from [@binsentsu](https://github.com/binsentsu).

### Features

- Installation through Config Flow UI.
- Separate sensor per register
- Auto applies scaling factor
- Configurable polling interval
- All modbus registers are read within 1 read cycle for data consistency between sensors.


### Configuration
Go to the integrations page in your configuration and click on new integration -> SAJ Modbus
