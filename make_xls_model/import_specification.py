"""Read model specification from Excel file.

Entry points:
   get_input_variables(abs_filepath)
   get_array_and_support_variables(abs_filepath)
   
   These functions return tuple of variables that can be unpacked as following:

   from import_specification import get_all_input_variables, get_array_and_support_variables 
   data_df, controls_df, equations_dict, var_group, var_desc_dict = get_all_input_variables(abs_filepath) 
   ar, equations_dict = get_array_and_support_variables(abs_filepath)

Validation performed:
   all data varibales must be covered by equations
   years in data and control must be continious
   
Not checked:
   'data', 'control', 'equations' (and optionally 'names') sheets exist in workbook for --make mode
   'model' sheet for --update mode 
   left side of eqaution must contain only [t] time indices
   
"""

import pandas as pd
from formula_parser import make_eq_dict
   
###########################################################################
## Generic import from Excel workbook (using pandas)
###########################################################################

def read_array(filename, sheet):    
    df = read_sheet(filename, sheet, None)    
    return df.fillna("").astype(object).as_matrix().transpose()

def read_sheet(filename, sheet, header):    
    return pd.read_excel(filename, sheetname=sheet, header = header).transpose()
    
def read_df(filename, sheet):    
    return read_sheet(filename, sheet, 0)
    
def read_col(filename, sheet):    
    return read_sheet(filename, sheet, None).values.tolist()[0]  
    
###########################################################################
## Import model specification, make it available as dict or tuple 
###########################################################################
   
def get_data_df(file):
    return read_df(file, 'data') 

def get_controls_df(file):
    return read_df(file, 'controls') 

def get_equations(file):
    list_of_strings = read_col(file, 'equations')
    # todo: 
    #     parse_to_formula_dict must:
    #        - control left side of equations
    return  list_of_strings, make_eq_dict(list_of_strings)
    
def get_names_dict(file):
    df = read_sheet(file, 'names', None)
    m = df.as_matrix()
    return {var:desc for var, desc in zip(m[0], m[1])} 
    
def get_spec_as_dict(file):
    eq_list, eq_dict = get_equations(file)
   
    return   { 'data': get_data_df(file)    
       ,   'controls': get_controls_df(file) 
       ,  'equations': eq_dict
       }

def get_core_spec_as_tuple(file): 
    s = get_spec_as_dict(file)
    return s['data'], s['controls'], s['equations']

###########################################################################
## Entry points
###########################################################################

def get_all_input_variables(abs_filepath):
    validate_input_from_sheets(abs_filepath)
    return get_input_variables(abs_filepath)

def get_array_and_support_variables(abs_filepath, sheet, pivot_col):
    ar = read_array(abs_filepath, sheet)
    list_of_strings = ar[:,pivot_col]
    eq_dict = make_eq_dict(list_of_strings)    
    return ar, eq_dict    
    
def get_input_variables(abs_filepath):
    data_df, controls_df, equations_dict = get_core_spec_as_tuple(abs_filepath) 
    var_groups = get_variable_names_by_group(data_df, controls_df, equations_dict)
    eq_list, eq_dict = get_equations(abs_filepath)
    var_names_dict = get_names_dict(abs_filepath)
    return data_df, controls_df, equations_dict, var_groups, var_names_dict, eq_list
  
###########################################################################
## Grouped variables
###########################################################################
   
def get_variable_names_by_group(data_df, controls_df, equations_dict):
    """
    Obtain non-overlapping variable labels grouped into data, control 
    and equation-derived variables.    
    """
    
    # all variables from controls_df must persist in var_list (group 1 of variables)
    g1 = controls_df.columns.values.tolist()
    
    # group 2: variables in data_df not listed in control_df
    dvars = data_df.columns.values.tolist()
    g2 = [d for d in dvars if d not in g1]

    # group 3: variables on leftside of equations not listed in group 1 and 2
    evars = equations_dict.keys()
    g3 = [e for e in evars if e not in g1 + g2]
    
    # WARNINGS: in other dictionary this is 'controls' key, in plural
    return {'control': g1, 'data': g2, 'eq': g3}
    
###########################################################################
## Input validation
###########################################################################

def list_array(a):
    return  " ".join(str(x) for x in a)

def validate_input_from_sheets(abs_filepath):
    # Get model specification 
    data_df, controls_df, equations_dict = get_core_spec_as_tuple(abs_filepath) 
    var_group = get_variable_names_by_group(data_df, controls_df, equations_dict)
    # Invoke validations 
    validate_continious_year(data_df, controls_df)
    validate_coverage_by_equations(var_group, equations_dict)
    
def validate_continious_year(data_df, controls_df):
    # Data and controls must have continious timeline
    years1 = data_df.index.tolist() 
    years2 = controls_df.index.tolist()
    timeline = years1 + years2
    ref_timeline = [x for x in range(min(timeline), max(timeline) + 1)]
    if not timeline == ref_timeline:
        raise ValueError("Timeline derived from 'data' and 'controls' is not continious." +
            "\nData timeline: "      + list_array(years1)   +
            "\nControls timeline: "  + list_array(years2)   +
            "\nResulting timeline: " + list_array(timeline) +
            "\nExpected timeline: "  + list_array(ref_timeline)
            )

def validate_coverage_by_equations(var_group, equations_dict):    
    # Validate coverage of data_df with equations
    data_orphan_vars = [v for v in var_group["data"] if v not in equations_dict.keys()]
    if data_orphan_vars:
        print(data_orphan_vars)
        raise ValueError("All data variables must be covered by equations." +
                         "\nNot covered: " + list_array(data_orphan_vars))