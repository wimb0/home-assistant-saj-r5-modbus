import asyncio
import logging
import struct
from typing import Dict, Any, List, Optional, TypeAlias
from pymodbus.client.mixin import ModbusClientMixin
from .const import DEVICE_STATUSSES, FAULT_MESSAGES, ModbusClient, Lock
from .modbus_utils import try_read_registers

DataDict: TypeAlias = Dict[str, Any]

_LOGGER = logging.getLogger(__name__)

async def _read_modbus_data(
    client: ModbusClient,
    lock: Lock,
    start_address: int,
    count: int,
    decode_instructions: List[tuple],
    data_key: str,
    default_decoder: str = "16u",
    default_factor: float = 0.01,
    log_level_on_error: int = logging.ERROR
) -> DataDict:
    """Helper function to read and decode Modbus data."""
    try:
        regs = await try_read_registers(client, lock, 1, start_address, count)

        if not regs:
            _LOGGER.log(log_level_on_error, f"Error reading modbus data: No response for {data_key}")
            return {}

        new_data = {}
        index = 0

        for instruction in decode_instructions:
            key, method, factor = (instruction + (default_factor,))[:3]
            method = method or default_decoder

            if method == "skip_bytes":
                index += factor // 2
                continue

            if not key:
                continue

            try:
                raw_value = regs[index]

                if method == "16i":
                    value = client.convert_from_registers([raw_value], ModbusClientMixin.DATATYPE.INT16)
                elif method == "16u":
                    value = client.convert_from_registers([raw_value], ModbusClientMixin.DATATYPE.UINT16)
                elif method == "32u":
                    if index + 1 < len(regs):
                        value = client.convert_from_registers([raw_value, regs[index + 1]], ModbusClientMixin.DATATYPE.UINT32)
                        index += 1
                    else:
                        value = 0
                else:
                    value = raw_value

                new_data[key] = round(value * factor, 2) if factor != 1 else value
                index += 1

            except Exception as e:
                _LOGGER.log(log_level_on_error, f"Error decoding {key}: {e}")
                return {}

        return new_data

    except ValueError as ve:
        # Known error, e.g. Exception 131/0
        _LOGGER.info(f"Unsupported Modbus register for {data_key}: {ve}")
        return {}

    except Exception as e:
        _LOGGER.log(log_level_on_error, f"Error reading modbus data: {e}")
        return {}

async def read_modbus_inverter_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads basic inverter data using the pymodbus 3.9 API, without BinaryPayloadDecoder."""
    try:
        regs = await try_read_registers(client, lock, 1, 0x8F00, 29)
        data = {}
        index = 0

        # Basic parameters: devtype and subtype as 16-bit unsigned values
        for key in ["devtype", "subtype"]:
            value = client.convert_from_registers(
                [regs[index]], ModbusClientMixin.DATATYPE.UINT16
            )
            data[key] = value
            index += 1

        # Communication version: 16-bit unsigned, multiplied by 0.001 and rounded to 3 decimal places
        commver = client.convert_from_registers(
            [regs[index]], ModbusClientMixin.DATATYPE.UINT16
        )
        data["commver"] = round(commver * 0.001, 3)
        index += 1

        # Serial number and PC: 20 bytes each (equivalent to 10 registers)
        for key in ["sn", "pc"]:
            reg_slice = regs[index : index + 10]
            raw_bytes = b"".join(struct.pack(">H", r) for r in reg_slice)
            data[key] = raw_bytes.decode("ascii", errors="replace").strip()
            index += 10

        # Hardware version numbers: Each as 16-bit unsigned, multiplied by 0.001
        for key in ["dv", "mcv", "scv", "disphwversion", "ctrlhwversion", "powerhwversion"]:
            value = client.convert_from_registers(
                [regs[index]], ModbusClientMixin.DATATYPE.UINT16
            )
            data[key] = round(value * 0.001, 3)
            index += 1

        return data
    except Exception as e:
        _LOGGER.error(f"Error reading inverter data: {e}")
        return {}

async def read_modbus_realtime_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads real-time operating data."""
    decode_instructions = [
        ("mpvmode", None), ("faultMsg0", "32u"), ("faultMsg1", "32u"),
        ("faultMsg2", "32u"), (None, "skip_bytes", 8), ("errorcount", None),
        ("SinkTemp", "16i", 0.1), ("AmbTemp", "16i", 0.1),
        ("gfci", None), ("iso1", None), ("iso2", None), ("iso3", None), ("iso4", None),
    ]

    data = await _read_modbus_data(client, lock, 16388, 19, decode_instructions, 'realtime_data', default_factor=1)

    fault_messages = []
    for key in ["faultMsg0", "faultMsg1", "faultMsg2"]:
        fault_code = data.get(key, 0)
        fault_messages.extend([
            msg for code, msg in FAULT_MESSAGES[int(key[-1])].items()
            if int(fault_code) & code
        ])
        data[key] = fault_code

    data["mpvstatus"] = DEVICE_STATUSSES.get(data.get("mpvmode"), "Unknown")
    data["faultmsg"] = ", ".join(fault_messages).strip()[:254]
    
    if fault_messages:
        _LOGGER.error(f"Fault detected: {data['faultmsg']}")
        
    return data

async def read_additional_modbus_data_1_part_1(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the first part of additional operating data (Set 1), up to sensor pv4Power."""
    decode_instructions_part_1 = [
        ("BatTemp", "16i", 0.1), ("batEnergyPercent", None), (None, "skip_bytes", 2),
        ("pv1Voltage", None, 0.1), ("pv1TotalCurrent", None), ("pv1Power", None, 1),
        ("pv2Voltage", None, 0.1), ("pv2TotalCurrent", None), ("pv2Power", None, 1),
        ("pv3Voltage", None, 0.1), ("pv3TotalCurrent", None), ("pv3Power", None, 1),
        ("pv4Voltage", None, 0.1), ("pv4TotalCurrent", None), ("pv4Power", None, 1),
    ]

    return await _read_modbus_data(client, lock, 16494, 15, decode_instructions_part_1, 'additional_data_1_part_1', default_factor=0.01)

async def read_additional_modbus_data_1_part_2(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the second part of additional operating data (Set 1)."""
    decode_instructions_part_2 = [
        ("directionPV", None), ("directionBattery", "16i"), ("directionGrid", "16i"),
        ("directionOutput", None), (None, "skip_bytes", 14), ("TotalLoadPower", "16i"),
        ("CT_GridPowerWatt", "16i"), ("CT_GridPowerVA", "16i"),
        ("CT_PVPowerWatt", "16i"), ("CT_PVPowerVA", "16i"),
        ("pvPower", "16i"), ("batteryPower", "16i"),
        ("totalgridPower", "16i"), ("totalgridPowerVA", "16i"),
        ("inverterPower", "16i"), ("TotalInvPowerVA", "16i"),
        ("BackupTotalLoadPowerWatt", None), ("BackupTotalLoadPowerVA", None),
        ("gridPower", "16i"),
    ]
    
    return await _read_modbus_data(client, lock, 16533, 25, decode_instructions_part_2, 'additional_data_1_part_2', default_factor=1)

async def read_additional_modbus_data_2_part_1(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the first part of additional operating data (Set 2)."""
    data_keys_part_1 = [
        "todayenergy", "monthenergy", "yearenergy", "totalenergy",
        "bat_today_charge", "bat_month_charge", "bat_year_charge", "bat_total_charge",
        "bat_today_discharge", "bat_month_discharge", "bat_year_discharge", "bat_total_discharge",
        "inv_today_gen", "inv_month_gen", "inv_year_gen", "inv_total_gen",
    ]
    decode_instructions_part_1 = [(key, "32u", 0.01) for key in data_keys_part_1]

    return await _read_modbus_data(client, lock, 16575, 32, decode_instructions_part_1, 'additional_data_2_part_1')

async def read_additional_modbus_data_2_part_2(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the second part of additional operating data (Set 2)."""
    data_keys_part_2 = [
        "total_today_load", "total_month_load", "total_year_load", "total_total_load",
        "backup_today_load", "backup_month_load", "backup_year_load", "backup_total_load",
        "sell_today_energy", "sell_month_energy", "sell_year_energy", "sell_total_energy",
        "feedin_today_energy", "feedin_month_energy", "feedin_year_energy", "feedin_total_energy",
    ]
    decode_instructions_part_2 = [(key, "32u", 0.01) for key in data_keys_part_2]

    return await _read_modbus_data(client, lock, 16607, 32, decode_instructions_part_2, 'additional_data_2_part_2')

async def read_additional_modbus_data_3(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads additional operating data (Set 3) - first part."""
    decode_instructions_part_3 = [
        ("today_pv_energy2", "32u", 0.01), ("month_pv_energy2", "32u", 0.01),
        ("year_pv_energy2", "32u", 0.01), ("total_pv_energy2", "32u", 0.01),
        ("today_pv_energy3", "32u", 0.01), ("month_pv_energy3", "32u", 0.01),
        ("year_pv_energy3", "32u", 0.01), ("total_pv_energy3", "32u", 0.01),
        ("sell_today_energy_2", "32u", 0.01), ("sell_month_energy_2", "32u", 0.01),
        ("sell_year_energy_2", "32u", 0.01), ("sell_total_energy_2", "32u", 0.01),
        ("sell_today_energy_3", "32u", 0.01), ("sell_month_energy_3", "32u", 0.01),
        ("sell_year_energy_3", "32u", 0.01)
    ]

    return await _read_modbus_data(
        client, lock, 16695, 30, decode_instructions_part_3, 
        'additional_data_3', 
        log_level_on_error=logging.WARNING
    )

async def read_additional_modbus_data_3_2(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads additional operating data (Set 3) - second part."""
    decode_instructions_part_3_2 = [
        ("sell_total_energy_3", "32u", 0.01), ("feedin_today_energy_2", "32u", 0.01),
        ("feedin_month_energy_2", "32u", 0.01), ("feedin_year_energy_2", "32u", 0.01),
        ("feedin_total_energy_2", "32u", 0.01), ("feedin_today_energy_3", "32u", 0.01),
        ("feedin_month_energy_3", "32u", 0.01), ("feedin_year_energy_3", "32u", 0.01),
        ("feedin_total_energy_3", "32u", 0.01), ("sum_feed_in_today", "32u", 0.01),
        ("sum_feed_in_month", "32u", 0.01), ("sum_feed_in_year", "32u", 0.01),
        ("sum_feed_in_total", "32u", 0.01), ("sum_sell_today", "32u", 0.01),
        ("sum_sell_month", "32u", 0.01), ("sum_sell_year", "32u", 0.01),
        ("sum_sell_total", "32u", 0.01)
    ]

    return await _read_modbus_data(
        client, lock, 16725, 34, decode_instructions_part_3_2, 
        'additional_data_3_2', 
        log_level_on_error=logging.WARNING
    )


async def read_additional_modbus_data_4(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads data for grid parameters (R, S, and T phase)."""
    decode_instructions = [
        ("RGridVolt", None, 0.1), ("RGridCurr", "16i", 0.01), ("RGridFreq", None, 0.01),
        ("RGridDCI", "16i",1), ("RGridPowerWatt", "16i", 1),
        ("RGridPowerVA", None, 1), ("RGridPowerPF", "16i"),
        ("SGridVolt", None, 0.1), ("SGridCurr", "16i", 0.01), ("SGridFreq", None, 0.01),
        ("SGridDCI", "16i",1), ("SGridPowerWatt", "16i", 1),
        ("SGridPowerVA", None, 1), ("SGridPowerPF", "16i"),
        ("TGridVolt", None, 0.1), ("TGridCurr", "16i", 0.01), ("TGridFreq", None, 0.01),
        ("TGridDCI", "16i",1), ("TGridPowerWatt", "16i", 1),
        ("TGridPowerVA", None, 1), ("TGridPowerPF", "16i"),
    ]
    
    return await _read_modbus_data(client, lock, 16433, 21, decode_instructions, "grid_phase_data", default_factor=0.001)

async def read_inverter_phase_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads data for inverter phase parameters (R, S, and T phase)."""
    decode_instructions = [
        ("RInvVolt", "16u", 0.1),
        ("RInvCurr", "16i", 0.01),
        ("RInvFreq", "16u", 0.01),
        ("RInvPowerWatt", "16i", 1),
        ("RInvPowerVA", "16u", 1),
        ("SInvVolt", "16u", 0.1),
        ("SInvCurr", "16i", 0.01),
        ("SInvFreq", "16u", 0.01),
        ("SInvPowerWatt", "16i", 1),
        ("SInvPowerVA", "16u", 1),
        ("TInvVolt", "16u", 0.1),
        ("TInvCurr", "16i", 0.01),
        ("TInvFreq", "16u", 0.01),
        ("TInvPowerWatt", "16i", 1),
        ("TInvPowerVA", "16u", 1),
    ]
    
    return await _read_modbus_data(client, lock, 16454, 15, decode_instructions, "inverter_phase_data", default_factor=1)

async def read_offgrid_output_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads data for offgrid output parameters (R, S, and T phase)."""
    decode_instructions = [
        ("ROutVolt", "16u", 0.1),
        ("ROutCurr", "16u", 0.01),
        ("ROutFreq", "16u", 0.01),
        ("ROutDVI", "16i", 1),
        ("ROutPowerWatt", "16u", 1),
        ("ROutPowerVA", "16u", 1),
        ("SOutVolt", "16u", 0.1),
        ("SOutCurr", "16u", 0.01),
        ("SOutFreq", "16u", 0.01),
        ("SOutDVI", "16i", 1),
        ("SOutPowerWatt", "16u", 1),
        ("SOutPowerVA", "16u", 1),
        ("TOutVolt", "16u", 0.1),
        ("TOutCurr", "16u", 0.01),
        ("TOutFreq", "16u", 0.01),
        ("TOutDVI", "16i", 1),
        ("TOutPowerWatt", "16u", 1),
        ("TOutPowerVA", "16u", 1),
    ]
    
    return await _read_modbus_data(client, lock, 16469, 18, decode_instructions, "offgrid_output_data")

async def read_side_net_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads data for side-net parameters."""
    decode_instructions = [
        ("ROnGridOutVolt", "16u", 0.1),
        ("ROnGridOutCurr", "16u", 0.01),
        ("ROnGridOutFreq", "16u", 0.01),
        ("ROnGridOutPowerWatt", "16u", 1),
        ("SOnGridOutVolt", "16u", 0.1),
        ("SOnGridOutPowerWatt", "16u", 1),
        ("TOnGridOutVolt", "16u", 0.1),
        ("TOnGridOutPowerWatt", "16u", 1),
    ]
    
    return await _read_modbus_data(client, lock, 16525, 8, decode_instructions, "side_net_data")

async def read_battery_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads battery data from registers 40960 to 41015."""
    decode_instructions = [
        ("BatNum", None, 1), ("BatCapcity", None, 1), ("Bat1FaultMSG", None, 1), ("Bat1WarnMSG", None, 1),
        ("Bat2FaultMSG", None, 1), ("Bat2WarnMSG", None, 1), ("Bat3FaultMSG", None, 1), ("Bat3WarnMSG", None, 1),
        ("Bat4FaultMSG", None, 1), ("Bat4WarnMSG", None, 1), ("BatUserCap", None, 1), ("BatOnline", None, 1),
        ("Bat1SOC", None), ("Bat1SOH", None), ("Bat1Voltage", None, 0.1), ("Bat1Current", "16i"),
        ("Bat1Temperature", "16i", 0.1), ("Bat1CycleNum", None, 1), ("Bat2SOC", None), ("Bat2SOH", None),
        ("Bat2Voltage", None, 0.1), ("Bat2Current", "16i"), ("Bat2Temperature", "16i", 0.1),
        ("Bat2CycleNum", None, 1), ("Bat3SOC", None), ("Bat3SOH", None), ("Bat3Voltage", None, 0.1),
        ("Bat3Current", "16i"), ("Bat3Temperature", "16i", 0.1), ("Bat3CycleNum", None, 1),
        ("Bat4SOC", None), ("Bat4SOH", None), ("Bat4Voltage", None, 0.1), ("Bat4Current", "16i"),
        ("Bat4Temperature", "16i", 0.1), ("Bat4CycleNum", None, 1), (None, "skip_bytes", 12),
        ("Bat1DischarCap", "32u", 1), ("Bat2DischarCap", "32u", 1), ("Bat3DischarCap", "32u", 1), ("Bat4DischarCap", "32u", 1),
        ("BatProtHigh", None, 0.1), ("BatProtLow", None, 0.1), ("Bat_Chargevoltage", None, 0.1), ("Bat_DisCutOffVolt", None, 0.1),
        ("BatDisCurrLimit", None, 0.1), ("BatChaCurrLimit", None, 0.1),
    ]
    
    return await _read_modbus_data(client, lock, 40960, 56, decode_instructions, 'battery_data', default_factor=0.01)

def decode_time(value: int) -> str:
    """Decodes a time value from the inverter format to a string representation.
    
    Args:
        value: The raw time value from the inverter
        
    Returns:
        A string in the format "HH:MM"
    """
    return f"{(value >> 8) & 0xFF:02d}:{value & 0xFF:02d}"

async def read_charge_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the Charge registers."""
    # Read the Charge registers directly with the sensor names
    decode_instructions = [
        ("charge_start_time", "16u", 1),
        ("charge_end_time", "16u", 1),
        ("charge_power_raw", "16u", 1),
    ]

    data = await _read_modbus_data(client, lock, 0x3606, 3, decode_instructions, "charge_data", default_factor=1)

    if data:
        try:
            # Decode the time values
            data["charge_start_time"] = decode_time(data["charge_start_time"])
            data["charge_end_time"] = decode_time(data["charge_end_time"])
            
            # Extract day_mask and power_percent from the third register
            power_value = data.pop("charge_power_raw")
            data["charge_day_mask"] = (power_value >> 8) & 0xFF
            data["charge_power_percent"] = power_value & 0xFF
        except Exception as e:
            _LOGGER.error(f"Error processing Charge data: {e}")
            return {}

    return data

async def read_discharge_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads all Discharge registers at once (discharge 1-7)."""
    # Read all Discharge registers directly with the sensor names
    decode_instructions = [
        # Discharge 1
        ("discharge_start_time", "16u", 1),
        ("discharge_end_time", "16u", 1),
        ("discharge_power_raw", "16u", 1),
        # Discharge 2
        ("discharge2_start_time", "16u", 1),
        ("discharge2_end_time", "16u", 1),
        ("discharge2_power_raw", "16u", 1),
        # Discharge 3
        ("discharge3_start_time", "16u", 1),
        ("discharge3_end_time", "16u", 1),
        ("discharge3_power_raw", "16u", 1),
        # Discharge 4
        ("discharge4_start_time", "16u", 1),
        ("discharge4_end_time", "16u", 1),
        ("discharge4_power_raw", "16u", 1),
        # Discharge 5
        ("discharge5_start_time", "16u", 1),
        ("discharge5_end_time", "16u", 1),
        ("discharge5_power_raw", "16u", 1),
        # Discharge 6
        ("discharge6_start_time", "16u", 1),
        ("discharge6_end_time", "16u", 1),
        ("discharge6_power_raw", "16u", 1),
        # Discharge 7
        ("discharge7_start_time", "16u", 1),
        ("discharge7_end_time", "16u", 1),
        ("discharge7_power_raw", "16u", 1),
    ]

    data = await _read_modbus_data(client, lock, 0x361B, 21, decode_instructions, "discharge_data", default_factor=1)

    if data:
        try:
            # Process the data for all discharges
            for prefix in ["discharge", "discharge2", "discharge3", "discharge4", "discharge5", "discharge6", "discharge7"]:
                # Decode the time values
                if f"{prefix}_start_time" in data:
                    data[f"{prefix}_start_time"] = decode_time(data[f"{prefix}_start_time"])
                
                if f"{prefix}_end_time" in data:
                    data[f"{prefix}_end_time"] = decode_time(data[f"{prefix}_end_time"])
                
                # Extract day_mask and power_percent from the third register
                if f"{prefix}_power_raw" in data:
                    power_value = data.pop(f"{prefix}_power_raw")
                    data[f"{prefix}_day_mask"] = (power_value >> 8) & 0xFF
                    data[f"{prefix}_power_percent"] = power_value & 0xFF
        except Exception as e:
            _LOGGER.error(f"Error processing discharge data: {e}")
            return {}

    return data



async def read_anti_reflux_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the Anti-Reflux registers using the generic read_modbus_data function."""
    decode_instructions = [
        ("AntiRefluxPowerLimit", "16u", 1),
        ("AntiRefluxCurrentLimit", "16u", 1),
        ("AntiRefluxCurrentmode_raw", "16u", 1),
    ]

    try:
        data = await _read_modbus_data(client, lock, 0x365A, 3, decode_instructions, "anti_reflux_data", default_factor=1)
        
        
        # Conversion of the AntiRefluxCurrentmode value to text
        if "AntiRefluxCurrentmode_raw" in data:
            mode_value = data.pop("AntiRefluxCurrentmode_raw")
            mode_text = {
                0: "0: Not open anti-reflux",
                1: "1: Total power mode",
                2: "2: Phase current mode",
                3: "3: Phase power mode"
            }.get(mode_value, f"Unknown mode ({mode_value})")
            
            data["AntiRefluxCurrentmode"] = mode_text
        
        return data
    except Exception as e:
        _LOGGER.error(f"Error reading Anti-Reflux data: {e}")
        return {}

async def read_passive_battery_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads the Passive Charge/Discharge and Battery configuration registers."""
    decode_instructions = [
        ("Passive_charge_enable", "16u", 1),
        ("Passive_GridChargePower", "16u"),
        ("Passive_GridDisChargePower", "16u"),
        ("Passive_BatChargePower", "16u"),
        ("Passive_BatDisChargePower", "16u"),
        (None, "skip_bytes", 18),  # Skip registers 363B-3643
        ("BatOnGridDisDepth", "16u", 1),
        ("BatOffGridDisDepth", "16u", 1),
        ("BatcharDepth", "16u", 1),
        ("AppMode", "16u", 1),
        (None, "skip_bytes", 10),  # Skip registers between AppMode (3647h) and BatChargePower (364Dh)
        ("BatChargePower", "16u"),  # Register 364Dh
        ("BatDischargePower", "16u"),  # Register 364Eh
        ("GridChargePower", "16u"),  # Register 364Fh
        ("GridDischargePower", "16u"),  # Register 3650h
    ]

    try:
        data = await _read_modbus_data(client, lock, 0x3636, 27, decode_instructions, "passive_battery_data", default_factor=0.1)
        return data
    except Exception as e:
        _LOGGER.error(f"Error reading Passive Battery data: {e}")
        return {}

async def read_meter_a_data(client: ModbusClient, lock: Lock) -> DataDict:
    """Reads Meter A data."""
    decode_instructions = [
        ("Meter_A_Volt1", "16u", 0.1),
        ("Meter_A_Curr1", "16i", 0.01),
        ("Meter_A_PowerW", "16i", 1),
        ("Meter_A_PowerV", "16u", 1),
        ("Meter_A_PowerFa", "16i", 0.001),
        ("Meter_A_Freq1", "16u", 0.01),
        ("Meter_A_Volt2", "16u", 0.1),
        ("Meter_A_Curr2", "16i", 0.01),
        ("Meter_A_PowerW_2", "16i", 1),
        ("Meter_A_PowerV_2", "16u", 1),
        ("Meter_A_PowerFa_2", "16i", 0.001),
        ("Meter_A_Freq2", "16u", 0.01),
        ("Meter_A_Volt3", "16u", 0.1),
        ("Meter_A_Curr3", "16i", 0.01),
        ("Meter_A_PowerW_3", "16i", 1),
        ("Meter_A_PowerV_3", "16u", 1),
        ("Meter_A_PowerFa_3", "16i", 0.001),
        ("Meter_A_Freq3", "16u", 0.01),
    ]

    return await _read_modbus_data(client, lock, 0xA03D, 18, decode_instructions, "meter_a_data")
