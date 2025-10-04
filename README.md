
Support the original SAJ R5 creator which this is based off.
<a href="https://buymeacoffee.com/wimbo" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/white_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

## SAJ R6 Inverter Modbus - Modified hub.py to align to the R6 registers.

### Features

- Installation through Config Flow UI.
- Separate sensor per register
- Auto applies scaling factor
- Configurable polling interval


### Configuration
Go to the integrations page in your configuration and click on new integration -> SAJ R6 Modbus


## Connection via Modbus TCP to a SAJ R5 Inverter via the RS485 port
Connect a Modbus to Wifi device to the Modbus port of your SAJ Inverter.

Guide below uses a Hi-Flying Elfin-EW11 (www.hi-flying.com/elfin-ew10-elfin-ew11).

**Cable Layout for EW11A to SAJ R6 Inverter:**

Both connectors are RJ45.
You will need to self-power the EW11 using an external power supply as the R6 does not provide power to the EW11 unlike the R5 does.

| SAJ RJ45 pin | Function | EW11 RJ45 pin |
|----------|----------|----------|
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



 ##  Credits
Credit to https://github.com/wimb0/home-assistant-saj-r5-modbus


Idea based on [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) from [@binsentsu](https://github.com/binsentsu).
 
[![saj_logo](https://github.com/wimb0/home-assistant-saj-r5-modbus/blob/main/images/saj_modbus/logo.png)](https://www.saj-electric.com/)

<!-- Badges -->


<!-- References -->

[home-assistant]: https://www.home-assistant.io/
[hacs]: https://hacs.xyz
[release-url]: https://github.com/wimb0/home-assistant-saj-r5-modbus/releases