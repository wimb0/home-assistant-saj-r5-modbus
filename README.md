[![hacs][hacs-badge]][hacs-url]
[![release][release-badge]][release-url]
![downloads][downloads-badge]

## SAJ R5 Inverter Modbus - A Home Assistant custom component for SAJ R5, Sununo and Suntrio inverters

Home assistant Custom Component for reading data from SAJ R5, Sununo and Suntrio Inverters through modbus TCP.

SAJ R5 Inverters are also sold in The Netherlands as Zonneplan ONE inverters.

Implements SAJ Inverter registers from [`saj-plus-series-inverter-modbus-protocal.pdf`](https://github.com/wimb0/home-assistant-saj-r5-modbus/blob/main/saj-plus-series-inverter-modbus-protocal.pdf).


### Features

- Installation through Config Flow UI.
- Separate sensor per register
- Auto applies scaling factor
- Configurable polling interval
- All modbus registers are read within 1 read cycle for data consistency between sensors.


### Configuration
Go to the integrations page in your configuration and click on new integration -> SAJ R5 Modbus

Home Assistant Custom Component for reading data from SAJ R5, Sununo and Suntrio Inverters through modbus over TCP.
This integration should work with SAJ R5, Sununo and Suntrio inverters.

## Installation

SAJ R5 Inverter Modus is available in [HACS][hacs] (Home Assistant Community Store).

Use this link to directly go to the repository in HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wimb0&repository=home-assistant-saj-r5-modbus)

_or_

1. Install HACS if you don't have it already
2. Open HACS in Home Assistant
3. Search for "SAJ R5 Inverter Modus"
4. Click the download button.


## Connection via Modbus TCP to a SAJ R5 Inverter via the RS485 port
Connect a Modbus to Wifi device to the Modbus port of your SAJ Inverter.

Guide below uses a Hi-Flying Elfin-EW11 (www.hi-flying.com/elfin-ew10-elfin-ew11).

**Cable Layout for EW11A to SAJ R5 Inverter:**

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


## Connection via Serial TCP to a SAJ R5 Inverter via the USB port
Connect a Modbus to Wifi device to the USB style port of your SAJ Inverter.

Tested using a Hi-Flying Elfin-EW10 (www.hi-flying.com/elfin-ew10-elfin-ew11).

**Cable Layout for EW10 to SAJ R5 Inverter:**

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

 ##  Credits

 Idea based on [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) from [@binsentsu](https://github.com/binsentsu).
 
[![saj_logo](https://github.com/wimb0/home-assistant-saj-r5-modbus/blob/main/images/saj_modbus/logo.png)](https://www.saj-electric.com/)

<!-- Badges -->
[hacs-url]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/hacs-default-orange.svg?style=flat-square
[release-badge]: https://img.shields.io/github/v/release/wimb0/home-assistant-saj-r5-modbus?style=flat-square
[downloads-badge]: https://img.shields.io/github/downloads/wimb0/home-assistant-saj-r5-modbus/total?style=flat-square

<!-- References -->

[home-assistant]: https://www.home-assistant.io/
[hacs]: https://hacs.xyz
[release-url]: https://github.com/wimb0/home-assistant-saj-r5-modbus/releases
