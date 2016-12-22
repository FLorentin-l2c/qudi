# -*- coding: utf-8 -*-
"""
This file contains the Qudi counter logic class.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic


class PulsedExtractionExternalLogic(GenericLogic):

    """ This logic module helps display user data in plots, and makes it easy to save.

    @signal sigCounterUpdate: there is new counting data available
    @signal sigCountContinuousNext: used to simulate a loop in which the data
                                    acquisition runs.
    @sigmal sigCountGatedNext: ???
    """

    _modclass = 'PulsedExtractionExternalLogic'
    _modtype = 'logic'

    # declare connectors
    _in = {'savelogic': 'SaveLogic',
           'pulseextractionlogic': 'PulseExtractionLogic',
           'pulseanalysislogic': 'PulseAnalysisLogic'}
    _out = {'pulsedextractionexternallogic': 'PulsedExtractionExternalLogic'}

    def __init__(self, **kwargs):
        """ Create QdplotLogic object with connectors.

        @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self, e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event
                         the state before the event happens and the destination
                         of the state which should be reached after the event
                         has happen.
        """


        self._save_logic = self.get_in_connector('savelogic')
        self._pe_logic = self.get_in_connector('pulseextractionlogic')
        self._pa_logic = self.get_in_connector('pulseanalysislogic')

    def on_deactivate(self, e):
        """ Deinitialisation performed during deactivation of the module.

        @param object e: Event class object from Fysom. A more detailed
                         explanation can be found in method activation.
        """
        return

    def load_data(self,len_header,column,filename):
        self.data = np.genfromtxt(filename,skip_header=len_header,usecols=column)
        return self.data

    def extract_laser_pulses(self,method,ignore_first,param_dict):
        if method =='Niko':
            number_laser=param_dict['number_laser']
            conv=param_dict['conv']
            laser_y = self._pe_logic.ungated_extraction(self.data,conv,number_laser)
        elif method == 'treshold':
            count_treshold=param_dict['count_treshold']
            min_len_laser=param_dict['min_len_laser']
            exception=param_dict['exception']
            laser_y = self._pe_logic.extract_laser_pulses(self.data,count_treshold,min_len_laser,exception)
        elif method == 'old':
            aom_delay=param_dict['aom_delay']
            initial_offset=param_dict['initial_offset']
            initial_length=param_dict['initial_length']
            increment_length=param_dict['increment_length']
            laser_y = self._pe_logic.excise_laser_pulses(self.data,aom_delay,
                                                         initial_offset,initial_length,increment_length)
        else:
            self.log.warning('Not yet implemented')
        if ignore_first:
            #laser_x=laser_x[1:][:]
            laser_y=laser_y[1:][:]
        #return laser_x,laser_y
        return laser_y

    def length_laser_pulses(self,laser):
        return len(laser)

    def sum_pulses(self,laser_2):
        return np.sum(laser_2,axis=0)


    def analyze_data(self, laser_data, norm_start_bin, norm_end_bin, signal_start_bin,
                     signal_end_bin):

        self.signal,self.measuring_error=self._pa_logic.analyze_data(laser_data,norm_start_bin,norm_end_bin,
                                                   signal_start_bin,signal_end_bin)
        return self.signal,self.measuring_error

    def compute_x_values(self,start,increment,alternating):
        if alternating:
            x_values=np.linspace(0,len(self.signal)/2-1,len(self.signal)/2)*increment+start
        else:
            x_values=np.linspace(0,len(self.signal)-1,len(self.signal))*increment+start
        return x_values


    def save_file(self):

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time (s)'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))
        parameters['Count frequency (Hz)'] = self._count_frequency
        parameters['Oversampling (Samples)'] = self._counting_samples
        parameters['Smooth Window Length (# of events)'] = self._smooth_window_length


        data = {'Time(s),Fluorescence(a.u.)': self.signal_data}
        fig = self.draw_figure(data=np.array(self._data_to_save))

        filelabel='result'
        filepath = self._save_logic.get_path_for_module(module_name='Counter')

        self._save_logic.save_data(data,
                                       filepath,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       as_text=True,
                                       plotfig=fig
                                       )
        plt.close(fig)

        return self._data_to_save, parameters

    def save_figure(self):
        pass


    def get_analysis_methods(self):
        return ('Niko','treshold','old')



