[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
## SAJ Inverter Modbus - A Home Assistant custom component for SAJ R5, Sununo and Suntrio inverters

Home assistant Custom Component for reading data from SAJ R5, Sununo and Suntrio Inverters through modbus TCP.

SAJ R5 Inverters are also sold in The Netherlands as Zonneplan ONE inverters.

Implements SAJ Inverter registers from [`saj-plus-series-inverter-modbus-protocal.pdf`](https://github.com/wimb0/home-assistant-saj-modbus/blob/main/saj-plus-series-inverter-modbus-protocal.pdf).

Idea based on [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) from [@binsentsu](https://github.com/binsentsu).

### Features

- Installation through Config Flow UI.
- Separate sensor per register
- Auto applies scaling factor
- Configurable polling interval
- All modbus registers are read within 1 read cycle for data consistency between sensors.


### Configuration
Go to the integrations page in your configuration and click on new integration -> SAJ Modbus

Home Assistant Custom Component for reading data from SAJ R5, Sununo and Suntrio Inverters through modbus over TCP.
This integration should work with SAJ R5, Sununo and Suntrio inverters.

## Installation
This integration is available in the HACS default repository.

Search for "SAJ R5, Sununo and Suntrio Inverter Modus" and install it.

After reboot of Home-Assistant, this integration can be configured through the integration setup UI

## Connection via Modbus TCP to a SAJ Inverter via the RS485 port
Connect a Modbus to Wifi device to the Modbus port of your SAJ Inverter.

Guide below uses a Hi-Flying Elfin-EW11 (www.hi-flying.com/elfin-ew10-elfin-ew11).

**Cable Layout for EW11A to SAJ Inverter:**

Both connectors are RJ45.
| SAJ RJ45 pin | Function | EW11 RJ45 pin |
|----------|----------|----------|
| 2        | GND_W    | 8        |
| 3        | +7V_W    | 7        |
| 7        | RS485_A+ | 5        |
| 8        | RS485_B+ | 6        |

**EW11A settings:**

**Communication settings:**
* Configure Tcp Server, choose a port number.
* Security: Disable
* Route as Uart

**Serial port settings:**
* Baudrate 9600
* Databit 8
* Stopbit 1
* Parity None
* Cli Disable
* Protocol Modbus


## Connection via Serial TCP to a SAJ Inverter via the USB port
Connect a Modbus to Wifi device to the USB style port of your SAJ Inverter.

Tested using a Hi-Flying Elfin-EW10 (www.hi-flying.com/elfin-ew10-elfin-ew11).

**Cable Layout for EW10 to SAJ Inverter:**

Cut an old USB-A cable and connect as follows:

| USB pin | Function   | EW10 pin |
|---------|------------|----------|
| 1       | +7V        | 7        |
| 2       | RS-232 RXD | 6        |
| 3       | RS-232 TXD | 5        |
| 4       | GND        | 8        |
**EW10 settings:**

**Communication settings:**
* Configure Tcp Server, choose a port number.
* Security: Disable
* Route as Uart

**Serial port settings:**
* Baudrate 115200
* Databit 8
* Stopbit 1
* Parity None
* Flow Control Settings Disable
* Cli Disable
* Protocol Modbus

  
[![saj_logo](https://github.com/wimb0/home-assistant-saj-modbus/blob/main/images/saj_modbus/logo.png)](https://www.saj-electric.com/)

