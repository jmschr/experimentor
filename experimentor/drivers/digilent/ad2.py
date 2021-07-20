# ##############################################################################
#  Copyright (c) 2021 Aquiles Carattino, Dispertech B.V.                       #
#  ad2.py is part of Experimentor.                                             #
#  This file is released under an MIT license.                                 #
#  See LICENSE.MD for more information.                                        #
# ##############################################################################

"""
Drivers for the Analog Discovery 2 board (they may also work with other boards). The idea is to wrap the methods
that appear in the examples to make them more "Pythonic". At the time of writing (July 2021), Digilent has provided
only with a low-level c-API library that is filled with values passed by reference and other patterns that are not
common for a Python developer.

This driver is not aimed at being exhaustive but rather focused on the objectives at hand, namely using the analog
acquisition synchronized via an external trigger (which can also be on the board itself).
"""
import sys
from ctypes import byref, c_bool, c_byte, c_double, c_int, cdll, create_string_buffer

import numpy as np

from experimentor.drivers.digilent.dwfconst import AcquisitionMode, AnalogAcquisitionFilter, AnalogInTriggerMode, \
    InstrumentState, \
    TriggerLength, TriggerSlope, TriggerSource
from experimentor.drivers.exceptions import DriverException
from experimentor.lib.log import get_logger

logger = get_logger()

try:
    if sys.platform.startswith("win"):
        dwf = cdll.dwf
    elif sys.platform.startswith("darwin"):
        dwf = cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
    else:
        dwf = cdll.LoadLibrary("libdwf.so")
except:
    logger.error("The library for controlling the digilent cards was not found. Please check your own "
                 "installation before proceeding")


class AnalogDiscovery:
    def __init__(self):
        self.hdwf = c_int()

    def initialize(self, dev_num=-1):
        """ Initialize the communication with a device identified by its order

        Parameters
        ----------
        dev_num : int
            The device number to open, by default it opens the last device

        Raises
        ------
        DriverException
            If the device can't be opened
        """

        dwf.FDwfDeviceOpen(c_int(dev_num), byref(self.hdwf))

        if self.hdwf.value == 0:
            szerr = create_string_buffer(512)
            dwf.FDwfGetLastErrorMsg(szerr)
            raise DriverException(str(szerr.value))

    def analog_out_count(self):
        """The number of analog output channels available on this board.

        Returns
        -------
        int
            The number of analog channels available
        """
        num_channels = c_int()
        dwf.FDwfAnalogOutCount(self.hdwf, byref(num_channels))
        return num_channels.value

    def analog_in_reset(self):
        dwf.FDwfAnalogInReset(self.hdwf)

    def analog_in_configure(self, reconfigure=1, start=1):
        dwf.FDwfAnalogInConfigure(self.hdwf, c_int(reconfigure), c_int(start))

    def analog_in_status(self, read_data=0):
        """ Checks the status of the acquisition

        Parameters
        ----------
        read_data : int
            0 or 1, to indicate whether data should be read from the device

        Returns
        -------
        InstrumentState
            The instrument state
        """
        state = c_byte()
        dwf.FDwfAnalogInStatus(self.hdwf, c_int(read_data), byref(state))
        return InstrumentState(state)

    def analog_in_samples_left(self):
        """
            Retrieves the number of samples left in the acquisition.
        Returns
        -------
        int
            Number of samples remaining
        """
        samples = c_int()
        dwf.FDwfAnalogInStatusSamplesLeft(self.hdwf, byref(samples))
        return samples.value

    def analog_in_samples_valid(self):
        samples = c_int()
        dwf.FDwfAnalogInStatusSamplesValid(self.hdwf, byref(samples))
        return samples.value

    def analog_in_status_index(self):
        """
        Retrieves the buffer write pointer which is needed in ScanScreen acquisition mode to display the scan bar.
        Returns
        -------
        int
            Variable to receive the position of the acquisition.
        """
        index = c_int()
        dwf.FDwfAnalogInStatusIndexWrite(self.hdwf, byref(index))
        return index.value

    def analog_in_status_auto_trigger(self):
        """
            Verifies if the acquisition is auto triggered.
        Returns
        -------
        int :
            I guess it returns 1 if the acquisition was auto triggered
        """
        auto = c_int()
        dwf.FDwfAnalogInStatusAutoTriggered(self.hdwf, byref(auto))
        return auto.value

    def analog_in_status_data(self, channel, samples, buffer=None):
        """ Retrieves the acquired data samples from the specified idxChannel on the AnalogIn instrument. It copies the
            data samples to the provided buffer.

        Parameters
        ----------
        channel : int
        samples : int
        buffer : c_double array, optional

        Returns
        -------
        np.array :
            Array with the data
        """
        if buffer is None:
            buffer = (c_double * samples)()
        dwf.FDwfAnalogInStatusData(self.hdwf, c_int(channel), byref(buffer), samples)
        return np.array(buffer)

    def analog_in_status_data_2(self, channel, first, samples, buffer=None):
        """
            Retrieves the acquired data samples from the specified idxChannel on the AnalogIn instrument. It copies the
            data samples to the provided buffer or creates a new buffer. This method allows to specify which data will
            be copied. To retrieve all data see :meth:`~analog_in_status_data`.

        Parameters
        ----------
        channel : int
        first : int
        samples : int
        buffer : c_double array, optional

        Returns
        -------
        numpy.array :
            Array with the data
        """
        if buffer is None:
            buffer = (c_double * samples)()
        dwf.FDwfAnalogInStatusData2(self.hdwf, c_int(channel), byref(buffer), c_int(first), c_int(samples))
        return np.array(buffer)

    def analog_in_status_data_16(self, channel, first, samples, buffer=None):
        """
        Retrieves the acquired raw data samples from the specified idxChannel on the AnalogIn instrument. It copies the
        data samples to the provided buffer or creates a new one. This is the **raw** data, as opposed to what
        :meth:`~analog_in_status_data` returns.

        Parameters
        ----------
        channel : int
        first : int
        samples : int
        buffer : c_double array, optional

        Returns
        -------
        numpy.array :
            Array with the data
        """
        if buffer is None:
            buffer = (c_double * samples)()
        dwf.FDwfAnalogInStatusData16(self.hdwf, c_int(channel), byref(buffer), c_int(first), c_int(samples))
        return np.array(buffer)

    def analog_in_status_noise(self, channel, samples):
        """ Retrieves the acquired noise samples from the specified idxChannel on the AnalogIn instrument.

        Parameters
        ----------
        channel : int
        samples : int

        Returns
        -------
        2-colum numpy.array :
            minimum noise data, maximum noise data
        """
        min_buffer = (c_double * samples)()
        max_buffer = (c_double * samples)()
        dwf.FDwfAnalogInStatusNoise(self.hdwf, c_int(channel), byref(min_buffer), byref(max_buffer), c_int(samples))
        min_buffer = np.array(min_buffer)
        max_buffer = np.array(max_buffer)
        return np.stack((min_buffer, max_buffer))

    def analog_in_status_sample(self, channel):
        """ Gets the last ADC conversion sample from the specified idxChannel on the AnalogIn instrument.

        Parameters
        ----------
        channel : int

        Returns
        -------
        float :
            Sample value
        """
        value = c_double()
        dwf.FDwfAnalogInStatusSample(self.hdwf, c_int(channel), byref(value))
        return value.value

    def analog_in_status_record(self):
        """ Retrieves information about the recording process. The data loss occurs when the device acquisition is
        faster than the read process to PC. In this case, the device recording buffer is filled and data samples are
        overwritten. Corrupt samples indicate that the samples have been overwritten by the acquisition process during
        the previous read. In this case, try optimizing the loop process for faster execution or reduce the acquisition
        frequency or record length to be less than or equal to the device buffer size
        (record length <= buffer size/frequency).


        Returns
        -------
        data_available : int
            Available number of samples
        data_lost : int
            Lost samples after the last check
        data_corrupt : int
            Number of samples that can be corrupt
        """
        data_available = c_int()
        data_lost = c_int()
        data_corrupt = c_int()

        dwf.FDwfAnalogInStatusRecord(self.hdwf, byref(data_available), byref(data_lost), byref(data_corrupt))
        return data_available.value, data_lost.value, data_corrupt.value

    def analog_in_record_length_set(self, length):
        dwf.FDwfAnalogInRecordLengthGet(self.hdwf, c_double(length))

    def analog_in_record_length_get(self):
        length = c_double()
        dwf.FDwfAnalogInRecordLengthSet(self.hdwf, byref(length))
        return length.value

    def analog_in_frequency_info(self):
        """ Retrieves the minimum and maximum (ADC frequency) settable sample frequency.

        Returns
        -------
        min_freq : float
            Minimum allowed frequency
        max_freq : float
            Maximum allowed frequency
        """
        min_freq = c_double()
        max_freq = c_double()
        dwf.FDwfAnalogInFrequencyInfo(self.hdwf, byref(min_freq), byref(max_freq))
        return min_freq.value, max_freq.value

    def analog_in_frequency_set(self, frequency):
        dwf.FDwfAnalogInFrequencySet(self.hdwf, c_double(frequency))

    def analog_in_frequency_get(self):
        frequency = c_double()
        dwf.FDwfAnalogInFrequencyGet(self.hdwf, byref(frequency))
        return frequency.value

    def analog_in_bits_info(self):
        bits = c_int()
        dwf.FDwfAnalogInBitsInfo(self.hdwf, byref(bits))
        return bits.value

    def analog_in_buffer_size_info(self):
        min_buff = c_int()
        max_buff = c_int()
        dwf.FDwfAnalogInBufferSizeInfo(self.hdwf, byref(min_buff), byref(max_buff))
        return min_buff.value, max_buff.value

    def analog_in_buffer_size_set(self, buffer_size):
        dwf.FDwfAnalogInBufferSizeSet(self.hdwf, c_int(buffer_size))

    def analog_in_buffer_size_get(self):
        buffer_size = c_int()
        dwf.FDwfAnalogInBufferSizeGet(self.hdwf, byref(buffer_size))
        return buffer_size.value

    def analog_in_noise_size_info(self):
        buffer_size = c_int()
        dwf.FDwfAnalogInNoiseSizeInfo(self.hdwf, byref(buffer_size))
        return buffer_size.value

    def analogin_noise_size_get(self):
        """
        Returns the used AnalogIn instrument noise buffer size. This is automatically adjusted according to the
        sample buffer size. For instance, having maximum buffer size of 8192 and noise buffer size of 512, setting the sample buffer size to 4096 the noise buffer size will be 256.

        Returns
        -------
        int :
            Current noise buffer size
        """
        noise_size = c_int()
        dwf.FDwfAnalogInNoiseSizeGet(self.hdwf, byref(noise_size))
        return noise_size.value

    def analog_in_acquisition_mode_info(self):
        """ Returns the supported AnalogIn acquisition modes. They are returned (by reference) as a bit field. This
        bit field can be parsed using the IsBitSet Macro. Individual bits are defined using the ACQMODE constants in dwf.h. The acquisition mode selects one of the following modes, ACQMODE:

        Returns
        -------
        int :
            Bitfield of modes, needs to be parsed
        """
        mode = c_int()
        dwf.FDwfAnalogInAcquisitionModeInfo(self.hdwf, byref(mode))
        return mode

    def analong_in_acquisition_mode_set(self, mode):
        """

        Parameters
        ----------
        mode : AcquisitionMode
        """
        dwf.FDwfAnalogInAcquisitionModeSet(self.hdwf, mode._value)

    def analog_in_acquisition_mode_get(self):
        """

        Returns
        -------
        AcquisitionMode :
            Current mode
        """
        mode = c_int()
        dwf.FDwfAnalogInAcquisitionModeGet(self.hdwf, byref(mode))
        return AcquisitionMode(mode)

    def analog_in_sampling_source_set(self, source):
        """

        Parameters
        ----------
        source : TriggerSource
        """
        dwf.FDwfAnalogInSamplingSourceSet(self.hdwf, source._value)

    def analog_in_sampling_source_get(self):
        source = c_int()
        dwf.FDwfAnalogInSamplingSourceGet(self.hdwf, byref(source))
        return TriggerSource(source)

    def analog_in_sampling_slope_set(self, slope):
        """

        Parameters
        ----------
        slope : TriggerSlope
        """
        dwf.FDwfAnalogInSamplingSlopeSet(self.hdwf, slope._value)

    def analog_in_sampling_slope_get(self):
        slope = c_int()
        dwf.FDwfAnalogInSamplingSlopeGet(self.hdwf, byref(slope))
        return TriggerSlope(slope)

    def analog_in_sampling_delay_set(self, delay):
        dwf.FDwfAnalogInSamplingDelaySet(self.hdwf, c_double(delay))

    def analog_in_sampling_delay_get(self):
        delay = c_double()
        dwf.FDwfAnalogInSamplingDelayGet(self.hdwf, byref(delay))
        return delay.value

    def analog_in_channel_count(self):
        count = c_int()
        dwf.FDwfAnalogInChannelCount(self.hdwf, byref(count))
        return count.value

    def analog_in_channel_enable(self, channel):
        """ Enables the specified channel. See :meth:`~analog_in_channel_disable`

        Parameters
        ----------
        channel : int
        """
        dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(channel), c_bool(True))

    def analog_in_channel_disable(self, channel):
        """ Disables the specified channel. See :meth:`~analog_in_channel_enable`

        Parameters
        ----------
        channel : int
        """
        dwf.FDwfAnalogInChannelEnableSet(self.hdwf, c_int(channel), c_bool(False))

    def analog_in_channel_enable_get(self, channel):
        enabled = c_int()
        dwf.FDwfAnalogInChannelEnableGet(self.hdwf, c_int(channel), byref(enabled))
        return enabled.value

    def analog_in_channel_filter_info(self):
        filter = c_int()
        dwf.FDwfAnalogInChannelFilterInfo(self.hdwf, byref(filter))
        return filter

    def analog_in_channel_filter_set(self, channel, filter):
        dwf.FDwfAnalogInChannelFilterSet(self.hdwf, c_int(channel), filter._value)

    def analog_in_channel_filter_get(self, channel):
        filter = c_int()
        dwf.FDwfAnalogInChannelFilterGet(self.hdwf, c_int(channel), byref(filter))
        return AnalogAcquisitionFilter(filter)

    def analog_in_channel_range_info(self):
        """

        Returns
        -------
        volts_min : float
        volts_max : float
        volts_steps : float
        """
        volts_min = c_double()
        volts_max = c_double()
        volts_steps = c_double()
        dwf.FDwfAnalogInChannelRangeInfo(self.hdwf, byref(volts_min), byref(volts_max), byref(volts_steps))
        return volts_min.value, volts_max.value, volts_steps.value

    def analog_in_channel_range_set(self, channel, channel_range):
        dwf.FDwfAnalogInChannelRangeSet(self.hdwf, c_int(channel), c_double(channel_range))

    def analog_in_channel_range_get(self, channel):
        channel_range = c_double()
        dwf.FDwfAnalogInChannelRangeGet(self.hdwf, c_int(channel), byref(channel_range))
        return channel_range.value

    def analog_in_channel_offset_info(self):
        volts_min = c_double()
        volts_max = c_double()
        steps = c_double()
        dwf.FDwfAnalogInChannelOffsetInfo(self.hdwf, byref(volts_min), byref(volts_max), byref(steps))
        return volts_min.value, volts_max.value, steps.value

    def analog_in_channel_offset_set(self, channel, offset):
        dwf.FDwfAnalogInChannelOffsetSet(self.hdwf, c_int(channel), c_double(offset))

    def analog_in_channel_offset_get(self, channel):
        offset = c_double()
        dwf.FDwfAnalogInChannelOffsetGet(self.hdwf, c_int(channel), byref(offset))
        return offset.value

    def analog_in_channel_attenuation_set(self, channel, attenuation):
        """
        Configures the attenuation for each channel. When channel index is specified as -1, each enabled AnalogIn
        channel attenuation will be configured to the same level. The attenuation does not change the attenuation on the device, just informs the library about the externally applied attenuation.
        Parameters
        ----------
        channel : int
        attenuation : float
        """
        dwf.FDwfAnalogInChannelAttenuationSet(self.hdwf, c_int(channel), c_double(attenuation))

    def analog_in_channel_attenuation_get(self, channel):
        attenuation = c_double()
        dwf.FDwfAnalogInChannelAttenuationGet(self.hdwf, c_int(channel), byref(attenuation))
        return attenuation.value

    def analog_in_trigger_source_set(self, source):
        dwf.FDwfAnalogInTriggerSourceSet(self.hdwf, source._value)

    def analog_in_trigger_source_get(self):
        source = c_int()
        dwf.FDwfAnalogInTriggerSourceGet(self.hdwf, byref(source))
        return TriggerSource(source)

    def analog_in_trigger_position_info(self):
        """
        Returns the minimum and maximum values of the trigger position in seconds.
        For Single/Repeated acquisition mode the horizontal trigger position is used is relative to the buffer middle point.
        For Record mode the position is relative to the start of the capture.

        .. todo:: The documentation specifies steps as double, but it makes more sense for it to be an integer. Other
            methods like :meth:`~analog_in_trigger_auto_timeout_info` use an integer

        Returns
        -------
        min_trigger : float
        max_trigger : float
        steps : float
        """
        min_trigger = c_double()
        max_trigger = c_double()
        steps = c_double()
        dwf.FDwfAnalogInTriggerPositionInfo(self.hdwf, byref(min_trigger), byref(max_trigger), byref(steps))
        return min_trigger.value, max_trigger.value, steps.value

    def analog_in_trigger_position_set(self, position):
        dwf.FDwfAnalogInTriggerPositionSet(self.hdwf, c_double(position))

    def analog_in_trigger_position_get(self):
        position = c_double()
        dwf.FDwfAnalogInTriggerPositionGet(self.hdwf, byref(position))
        return position.value

    def analog_in_trigger_auto_timeout_info(self):
        min_timeout = c_double()
        max_timeout = c_double()
        steps = c_int()
        dwf.FDwfAnalogInTriggerAutoTimeoutInfo(self.hdwf, byref(min_timeout), byref(max_timeout), byref(steps))
        return min_timeout.value, max_timeout.value, steps.value

    def analog_in_trigger_auto_timeout_set(self, timeout=0):
        dwf.FDwfAnalogInTriggerAutoTimeoutSet(self.hdwf, c_double(timeout))

    def analog_in_trigger_auto_timeout_get(self):
        timeout = c_double()
        dwf.FDwfAnalogInTriggerAutoTimeoutGet(self.hdwf, byref(timeout))
        return timeout.value

    def analog_in_trigger_holdoff_info(self):
        """ Returns the supported range of the trigger Hold-Off time in Seconds. The trigger hold-off is an
        adjustable period of time during which the acquisition will not trigger. This feature is used when you are triggering on burst waveform shapes, so the oscilloscope triggers only on the first eligible trigger point.

        Returns
        -------
        min_holdoff : float
        max_holdoff : float
        steps : float
        """
        min_holdoff = c_double()
        max_holdoff = c_double()
        steps = c_double()
        dwf.FDwfAnalogInTriggerHoldOffInfo(self.hdwf, byref(min_holdoff), byref(max_holdoff), byref(steps))
        return min_holdoff.value, max_holdoff.value, steps.value

    def analog_in_trigger_holdoff_set(self, holdoff):
        dwf.FDwfAnalogInTriggerHoldOffSet(self.hdwf, c_double(holdoff))

    def analog_in_trigger_holdoff_get(self):
        holdoff = c_double()
        dwf.FDwfAnalogInTriggerHoldOffGet(self.hdwf, byref(holdoff))
        return holdoff.value

    def analog_in_trigger_type_set(self, trig_type):
        dwf.FDwfAnalogInTriggerTypeSet(self.hdwf, trig_type._value)

    def analog_in_trigger_type_get(self):
        trig_type = c_int()
        dwf.FDwfAnalogInTriggerTypeGet(self.hdwf, byref(trig_type))
        return AnalogInTriggerMode(trig_type)

    def analog_in_trigger_channel_info(self):
        min_channel = c_int()
        max_channel = c_int()
        dwf.FDwfAnalogInTriggerChannelInfo(self.hdwf, byref(min_channel), byref(max_channel))
        return min_channel.value, max_channel.value

    def analog_in_trigger_channel_set(self, channel):
        """Sets the trigger channel."""
        dwf.FDwfAnalogInTriggerChannelSet(self.hdwf, c_int(channel))

    def analog_in_trigger_filter_info(self):
        """ Returns the supported trigger filters. They are returned (by reference) as a bit field which can be
        parsed using the IsBitSet Macro. Individual bits are defined using the FILTER constants in DWF.h. Select
        trigger detector sample source, FILTER:

            - filterDecimate: Looks for trigger in each ADC conversion, can detect glitches.
            - filterAverage: Looks for trigger only in average of N samples, given by :meth:`~analog_in_frequency_set`.
        """
        filter_info = c_int()
        dwf.FDwfAnalogInTriggerFilterInfo(self.hdwf, byref(filter_info))
        return filter_info.value

    def analog_in_trigger_filter_set(self, trig_filter):
        dwf.FDwfAnalogInTriggerFilterSet(self.hdwf, trig_filter._value)

    def analog_in_trigger_filter_get(self):
        trig_filter = c_int()
        dwf.FDwfAnalogInTriggerFilterGet(self.hdwf, byref(trig_filter))
        return AnalogAcquisitionFilter(trig_filter)

    def analog_in_trigger_channel_get(self):
        channel = c_int()
        dwf.FDwfAnalogInTriggerChannelGet(self.hdwf, byref(channel))
        return channel.value

    def analog_in_trigger_condition_info(self):
        """ Returns the supported trigger type options for the instrument. They are returned (by reference) as a bit
        field. This bit field can be parsed using the IsBitSet Macro. Individual bits are defined using the DwfTriggerSlope constants in dwf.h. These trigger condition options are:

            - DwfTriggerSlopeRise (This is the default setting):
                - For edge and transition trigger on rising edge.
                - For pulse trigger on positive pulse; For window exiting.
            - DwfTriggerSlopeFall
                - For edge and transition trigger on falling edge.
                - For pulse trigger on negative pulse; For window entering.
            - DwfTriggerSlopeEither
                - For edge and transition trigger on either edge.
                - For pulse trigger on either positive or negative pulse.
        Returns
        -------
        info : int
        """
        info = c_int()
        dwf.FDwfAnalogInTriggerConditionInfo(self.hdwf, byref(info))
        return info.value

    def analog_in_trigger_condition_set(self, condition):
        dwf.FDwfAnalogInTriggerConditionSet(self.hdwf, condition._value)

    def analog_in_trigger_condition_get(self):
        condition = c_int()
        dwf.FDwfAnalogInTriggerConditionSet(self.hdwf, byref(condition))
        return TriggerSlope(condition)

    def analog_in_trigger_level_info(self):
        volts_min = c_double()
        volts_max = c_double()
        steps = c_int()

        dwf.FDwfAnalogInTriggerLevelInfo(self.hdwf, byref(volts_min), byref(volts_max), byref(steps))
        return volts_min.value, volts_max.value, steps.value

    def analog_in_trigger_level_set(self, level):
        dwf.FDwfAnalogInTriggerLevelSet(self.hdwf, c_double(level))

    def analog_in_trigger_level_get(self):
        level = c_double()
        dwf.FDwfAnalogInTriggerLevelGet(self.hdwf, byref(level))
        return level.value

    def analog_in_trigger_hysteresis_info(self):
        """ Retrieves the range of valid trigger hysteresis voltage levels for the AnalogIn instrument in Volts. The
        trigger detector uses two levels: low level (TriggerLevel - Hysteresis) and high level (TriggerLevel + Hysteresis). Trigger hysteresis can be used to filter noise for Edge or Pulse trigger. The low and high levels are used in transition time triggering."""
        volts_min = c_double()
        volts_max = c_double()
        steps = c_int()

        dwf.FDwfAnalogInTriggerHysteresisInfo(self.hdwf, byref(volts_min), byref(volts_max), byref(steps))
        return volts_min.value, volts_max.value, steps.value

    def analog_in_trigger_hysteresis_set(self, level):
        dwf.FDwfAnalogInTriggerHysteresisSet(self.hdwf, c_double(level))

    def analog_in_trigger_hysteresis_get(self):
        level = c_double()
        dwf.FDwfAnalogInTriggerHysteresisGet(self.hdwf, byref(level))
        return level.value

    def analog_in_trigger_length_condition_info(self):
        """
        Returns the supported trigger length condition options for the AnalogIn instrument. They are returned (by
        reference) as a bit field. This bit field can be parsed using the IsBitSet Macro. Individual bits are defined
        using the TRIGLEN constants in DWF.h. These trigger length condition options are:

            - triglenLess: Trigger immediately when a shorter pulse or transition time is detected.
            - triglenTimeout: Trigger immediately as the pulse length or transition time is reached.
            - triglenMore: Trigger when the length/time is reached, and pulse or transition has ended.
        Returns
        -------
        supported trigger length conditions
        """
        condition = c_int()

        dwf.FDwfAnalogInTriggerLengthConditionInfo(self.hdwf, byref(condition))
        return condition.value

    def analog_in_trigger_length_condition_set(self, length):
        dwf.FDwfAnalogInTriggerLengthConditionSet(self.hdwf, length._value)

    def analog_in_trigger_length_condition_hysteresis_get(self):
        length = c_double()
        dwf.FDwfAnalogInTriggerHysteresisGet(self.hdwf, byref(length))
        return TriggerLength(length)

    def analog_in_trigger_length_info(self):
        """
        Returns the supported range of trigger length for the instrument in Seconds. The trigger length specifies the
        minimal or maximal pulse length or transition time.
        """
        min_length = c_double()
        max_length = c_double()
        steps = c_double()

        dwf.FDwfAnalogInTriggerLengthInfo(self.hdwf, byref(min_length), byref(max_length), byref(steps))
        return min_length.value, max_length.value, steps.value

    def analog_in_trigger_length_set(self, length):
        dwf.FDwfAnalogInTriggerLengthSet(self.hdwf, c_double(length))

    def analog_in_trigger_length_condition_get(self):
        length = c_double()
        dwf.FDwfAnalogInTriggerHysteresisGet(self.hdwf, byref(length))
        return length.value