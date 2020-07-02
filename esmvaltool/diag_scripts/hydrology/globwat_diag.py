"""globwat diagnostic."""
import logging
from pathlib import Path

import iris
from iris.pandas import as_data_frame
import dask.array as da
import numpy
import pandas as pd
import calendar
import os 

import subprocess
from esmvalcore import preprocessor as preproc
from esmvaltool.diag_scripts.hydrology.derive_evspsblpot import debruin_pet
from esmvaltool.diag_scripts.shared import (ProvenanceLogger,
                                            get_diagnostic_filename,
                                            group_metadata, run_diagnostic,
                                            select_metadata)


logger = logging.getLogger(Path('__file__').name) #for test in python use '__file__'


def create_provenance_record():
    """Create a provenance record."""
    record = {
        'caption': "Forcings for the GlobWat hydrological model.",
        'domains': ['global'],
        'authors': [
            'abdollahi_banafsheh',
            'alidoost_sarah',
        ],
        'projects': [
            'ewatercycle',
        ],
        'references': [
            'acknow_project',
        ],
        'ancestors': [],
    }
    return record

def change_data_type(cube):
    """GlobWat input data types are float32.
    """
    # fix dtype
    cube.data = cube.core_data().astype('float32')
    for coord_name in 'latitude', 'longitude', 'time':
        coord = cube.coord(coord_name)
        coord.points = coord.core_points().astype('float32')
        coord.bounds = None
        coord.guess_bounds()
    return cube

def get_input_cubes(metadata):
    """Return a dict with all (preprocessed) input files."""
    provenance = create_provenance_record()
    all_vars = {}
    for attributes in metadata:
        short_name = attributes['short_name']
        if short_name in all_vars:
            raise ValueError(
                f"Multiple input files found for variable '{short_name}'.")
        filename = attributes['filename']
        logger.info("Loading variable %s", short_name)
        cube = iris.load_cube(filename)
        #set filling values to -9999
        cube.data.set_fill_value(-9999)
        #change cube dtype to float32
        all_vars[short_name] = change_data_type(cube)
        provenance['ancestors'].append(filename)
    return all_vars, provenance


def _get_extra_info(cube):
    """Get start/end time and origin of cube.
    Get the start and end times as an array with length 6
    and get latitude and longitude as an array with length 2
    """
    coord = cube.coord('time')
    time_start_end = []
    for index in 0, -1:
        time_val = coord.cell(index).point
        time_val = [
            time_val.year,
            time_val.month,
            time_val.day,
            time_val.hour,
            time_val.minute,
            time_val.second,
        ]
        time_val = [float(time) for time in time_val]
        time_start_end.append(time_val)
    # Add data_origin
    lat_lon = [
        cube.coord(name).points[0] for name in ('latitude', 'longitude')
    ]
    return time_start_end, lat_lon

def _shift_era5_time_coordinate(cube):
    """Shift instantaneous variables 30 minutes forward in time.
    After this shift, as an example:
    time format [1990, 1, 1, 11, 30, 0] will be [1990, 1, 1, 12, 0, 0].
    For aggregated variables, already time format is [1990, 1, 1, 12, 0, 0].
    """
    time = cube.coord(axis='T')
    time.points = time.points + 30 / (24 * 60)
    time.bounds = None
    time.guess_bounds()
    return cube

def get_year_month_day_for_output_name(cube): 
    """get month and day number for output name."""
    # get start year and end year  
    coord_time = cube.coord('time') 
    start_year = coord_time.cell(0).point.year 
    end_year = coord_time.cell(-1).point.year 
    year = start_year - 1   
    #looping over time dimention, get day and months 
    months = [] 
    days = []     
    for i in range(0, len(cube.coord('time').points)):  
        n_month = str(coord_time.cell(i).point.month).zfill(2)
        months.append(n_month)
        nday = calendar.monthrange(year,int(n_month))[1] 
        for daynumber in range(1, nday+1):   
            days.append(str(n_month) + str(daynumber).zfill(2)) 
    return months ,days 
    
def make_output_name(cube):
    """Get output file name, specific to Globwat.""" 
    monthly_pr = [] 
    daily_pr = []
    monthly_pet = [] 
    daily_pet = [] 
    output_name = {'pr':{'Amon':{}, 'day':{}}, 'pet':{'Amon':{}, 'day':{}}}      
    months , days = get_month_day_for_output_name(cube) 
    for mip in 'Amon', 'day': 
        if mip == 'Amon': 
            for i in range (len(months)): 
                for shortname in ['pr', 'pet']: 
                    if shortname == 'pr':
                        monthly_pr.append('prc'+ str(months[i]) + 'wb.asc')
                    else:
                        monthly_pet.append('eto'+ str(months[i]) + 'wb.asc')           
        elif mip == 'day':
            for i in range(len(days)):
                for shortname in ['pr', 'pet']: 
                    if shortname == 'pr':
                        daily_pr.append('prc'+ str(days[i]) + 'wb.asc')
                    else:
                        daily_pet.append('eto'+ str(days[i]) + 'wb.asc')
    output_name['pr']['Amon'] = monthly_pr
    output_name['pr']['day'] = daily_pr
    output_name['pet']['Amon']  = monthly_pet
    output_name['pet']['day'] = daily_pet
    return output_name

def main(cfg):
    """Process data for use as input to the GlobWat hydrological model.

    These variables are needed in all_vars:
    evspsblpot (potential_evapotranspiration_flux)
    pr (precipitation_flux)
    psl (air_pressure_at_mean_sea_level)
    rsds (surface_downwelling_shortwave_flux_in_air)
    rsdt (toa_incoming_shortwave_flux)
    tas (air_temperature)
    """
    input_metadata = cfg['input_data'].values()
    # for checking the code in ipython I added print(input_metadata).
    # Run the script and use print(input_metadata) in the log.txt as input_metadata
    print(input_metadata)
    for dataset, metadata in group_metadata(input_metadata, 'dataset').items():
        all_vars, provenance = get_input_cubes(metadata)
        
        pr = all_vars['pr']
                
        logger.info("Potential evapotransporation not available, deriving")
        pet = debruin_pet(
            psl=all_vars['psl'],
            rsds=all_vars['rsds'],
            rsdt=all_vars['rsdt'],
            tas=all_vars['tas'],
        )
        logger.info("Converting units")
        pr.units = pr.units / 'kg m-3'
        pr.data = pr.core_data() / 1000.
     
        pet.units = pet.units / 'kg m-3'
        pet.data = pet.core_data() /1000.
            
        # cube = all_vars['pr']  

        # Unit conversion of pr and pet from 'kg m-2 s-1' to 'mm month-1'
        for mip in 'Amon', 'day':
            if mip == 'Amon':
                all_vars['pr'] = pr.convert_units('mm month-1')
                all_vars['pet'] = pet.convert_units('mm month-1')
            # Unit conversion of pr and pet from 'kg m-2 s-1' to 'mm day-1'
            elif mip == 'day':
                all_vars['pr'] = pr.convert_units('mm day-1')
                all_vars['pet'] = pet.convert_units('mm day-1')

        # output_file = get_diagnostic_filename(get_output_stem_monthly(cube),cfg, 'asc')
        #TODO: the input data has 6 rows as a header which then be skiped by the model
        # so here I should add 6 rows,otherwise the model skip the 6 rows of data  
        coord_time = cube.coord('time')                                         
        output_name = make_output_name(cube)
        start_year = coord_time.cell(0).point.year 
        end_year = coord_time.cell(-1).point.year 
        for nyear in range (start_year , end_year+1):
            path = os.path.join('GlobWat_Inputs', str(dataset),str(nyear))
            for key in ['pr', 'pet']:
                for mip in ['Amon', 'day']:
                    for i in range(len(output_name[key][mip])):
                        key_cube = all_vars[key]
                        for sub_cube in key_cube.slices_over('time'): 
                            frame = iris.pandas.as_data_frame(sub_cube, copy=True)
                            print(frame) 
                            final_path = os.path.join(path, output_name[key][mip][i])
                            # Path(output_file[i]).parent.mkdir(exist_ok=True)
                            frame.to_csv(os.makedirs(final_path),
                                        sep=' ',
                                        na_rep='-9999',
                                        float_format='%.1f'
                                        ) 
            # # Store provenance
            # with ProvenanceLogger(cfg) as provenance_logger:
            #     provenance_logger.log(output_file, provenance)



if __name__ == '__main__':
   with run_diagnostic() as config:
       main(config)