[![release][release-badge]][release-url]
![active][active-badge]
![downloads][downloads-badge]
[![hacs][hacs-badge]][hacs-url]
![license][lic-badge]

<a href="https://buymeacoffee.com/wimbo" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

# Home Assistant SAJ R5 Series Inverter Modbus Integration

This is an unofficial Home Assistant integration that enables you to read data locally from SAJ R5, Sununo, and Suntrio inverters via Modbus TCP, without a cloud-connected dongle.

The integration is also compatible with Zonneplan ONE inverters, which are rebranded SAJ R5 inverters.


Implements SAJ Inverter registers from [`saj-plus-series-inverter-modbus-protocal.pdf`](https://github.com/wimb0/home-assistant-saj-r5-modbus/blob/main/saj-plus-series-inverter-modbus-protocal.pdf).


## Features ✨

* **Easy Installation:** Set up (and reconfigure) the integration through the Home Assistant UI.
* **Detailed Sensors:** Each Modbus register is exposed as a separate sensor.
* **Automatic Scaling:** The integration automatically applies the correct scaling factor to the raw data.
* **Configurable Polling:** You can set your desired polling interval for data updates.
* **Data Consistency:** All realtime Modbus registers are read in a single cycle to ensure data consistency across all sensors.
* **Remote Control:** Turn the inverter on or off and limit the power output.
* **Set Date and Time:** A service is provided to set the date and time on your inverter.


## Configuration 🛠️

Once the integration is installed, you can configure it through the Home Assistant UI.

1.  Go to **Settings > Devices & Services**.
2.  Click the **+ Add Integration** button.
3.  Search for "SAJ R5 Modbus" and select it.
4.  Fill in the required information:
    * **Name:** A descriptive name for your inverter (e.g., "SAJ Inverter").
    * **Host:** The IP address of your Modbus to Wi-Fi device.
    * **Port:** The TCP port for the Modbus connection (default is 502).
    * **Scan Interval:** The frequency in seconds to poll the inverter for data (default is 60).


## Installation ⚙️

This integration is available in the Home Assistant Community Store [HACS][hacs].

Use this link to directly go to the repository in HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wimb0&repository=home-assistant-saj-r5-modbus)

_or_

1.  **Install HACS:** If you don't have HACS installed, follow the [installation instructions](https://hacs.xyz/docs/setup/download).
2.  **Add Integration:**
    * Open HACS in Home Assistant.
    * Go to "Integrations".
    * Click the three dots in the top right and select "Custom repositories".
    * Add the repository URL: `https://github.com/wimb0/home-assistant-saj-r5-modbus` and select the "Integration" category.
    * Search for "SAJ R5 Inverter Modbus" and click "Install".
3.  **Restart Home Assistant:** After installation, you must restart Home Assistant.


## Connecting to the Inverter 🔌
You will need a Modbus to Wi-Fi or Ethernet adapter to connect your SAJ inverter to your network.
The following instructions are for the Hi-Flying Elfin-EW11/EW10, but other similar devices should work as well.

<details>
<summary>Connection via RS485 Port (EW11A)</summary>

Connect the EW11A to the RS485 port on your SAJ R5 inverter.

**Cable Layout (RJ45 to RJ45):**

| SAJ RJ45 Pin | Function | EW11 RJ45 Pin |
| :---: | :---: | :---: |
| 2 | GND\_W | 8 |
| 3 | +7V\_W | 7 |
| 7 | RS485\_A+ | 5 |
| 8 | RS485\_B- | 6 |

**EW11A Settings:**

* **Communication Settings:**
    * **Protocol:** TCP Server
    * **Port:** Choose a port number (e.g., 502)
    * **Security:** Disable
* **Serial Port Settings:**
    * **Baud Rate:** 9600
    * **Data Bits:** 8
    * **Stop Bits:** 1
    * **Parity:** None
    * **Protocol:** Modbus
</details>

<details>
<summary>Connection via USB Port (EW10)</summary>

Connect the EW10 to the USB port on your SAJ R5 inverter. You will need to create a custom cable from an old USB-A cable.

**Cable Layout (USB-A to EW10):**

| USB Pin | Function | EW10 Pin |
| :---: | :---: | :---: |
| 1 | +7V | 7 |
| 2 | RS-232 RXD | 6 |
| 3 | RS-232 TXD | 5 |
| 4 | GND | 8 |

**EW10 Settings:**

* **Communication Settings:**
    * **Protocol:** TCP Server
    * **Port:** Choose a port number (e.g., 502)
    * **Security:** Disable
* **Serial Port Settings:**
    * **Baud Rate:** 115200
    * **Data Bits:** 8
    * **Stop Bits:** 1
    * **Parity:** None
    * **Flow Control:** Disable
    * **Protocol:** Modbus
</details>

## Entities 🧩

This integration will create the following entities:

### Sensors

* **Device Information:** Type, Sub Type, Comms Protocol Version, Serial Number, Product Code, and various hardware/software versions.
* **Status:** Inverter Status, Inverter Working Mode, and Inverter Error Message.
* **Real-time Data:** PV voltage, current, and power for each string, bus voltage, inverter temperature, and more.
* **Grid Information:** L1/L2/L3 voltage, current, frequency, and power.
* **Energy Production:** Daily, monthly, yearly, and total power generation.
* **Working Hours:** Daily and total working hours.

### Switches

* **Power On/Off:** A switch to remotely turn the inverter on or off.

### Numbers

* **Limit Power:** A number entity to limit the inverter's power output (in percentage).

### Services

* `saj_modbus.set_datetime` : This service allows you to set the date and time on the inverter. You can call this service from automations or scripts.


## Troubleshooting 🐛

If you encounter any issues with the integration, there are two main ways to gather more information to help diagnose the problem.

### Enabling Debug Logging

For detailed logs, you can enable debug logging for this integration by adding the following to your `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.saj_modbus: debug
```

After adding this, restart Home Assistant. The logs can be found in **Settings > System > Logs**.

### Downloading Diagnostics

You can download diagnostic data directly from Home Assistant. This data provides information about the inverter and the integration's status.

1.  Navigate to **Settings > Devices & Services**.
2.  Find the SAJ R5 Inverter Modbus integration and click on the device.
3.  Click the three-dot menu on the device card and select **Download diagnostics**.

This will download a text file with diagnostic information that you can share when creating a bug report.


## Credits 📣

This integration was inspired by the [`home-assistant-solaredge-modbus`](https://github.com/binsentsu/home-assistant-solaredge-modbus) integration by [@binsentsu](https://github.com/binsentsu).


_This is a third-party integration and is not officially supported by SAJ Electric._


[![saj_logo](https://github.com/wimb0/home-assistant-saj-r5-modbus/blob/main/images/saj_modbus/logo.png)](https://www.saj-electric.com/)

<!-- Badges -->


<!-- References -->

[home-assistant]: https://www.home-assistant.io/
[hacs]: https://hacs.xyz
[release-url]: https://github.com/wimb0/home-assistant-saj-r5-modbus/releases
