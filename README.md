[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![saj_logo](https://github.com/wimb0/home-assistant-saj-modbus/blob/main/images/saj_modbus/logo.png)

# home-assistant-saj-modbus
Home assistant Custom Component for reading data from SAJ inverters through modbus TCP.
SAJ Inverters are also sold in The Netherlands as Zonneplan ONE inverters.
Implements SAJ Inverter registers from [`saj-plus-series-inverter-modbus-protocal.pdf`](https://github.com/wimb0/home-assistant-saj-modbus/blob/main/saj-plus-series-inverter-modbus-protocal.pdf).

Based on [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) from [@binsentsu](https://github.com/binsentsu).

# Installation
Copy contents of custom_components folder to your home-assistant config/custom_components folder or install through HACS.
After reboot of Home-Assistant, this integration can be configured through the integration setup UI

# Connection via Modbus TCP to a SAJ Inverter
Connect a Modbus to Wifi device to the Modbus port of your SAJ Inverter.
I use a Hi-Flying Elfin-EW11 (www.hi-flying.com/elfin-ew10-elfin-ew11).

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
