#!/usr/bin/env python3

import argparse
import tempfile
import tarfile
import os
import glob

import sys
sys.path.insert(0, '/home/')
import rpToolServe

##
#
#
if __name__ == "__main__":
    parser = argparse.ArgumentParser('Given an SBML, extract the reaction rules and pass them to Selenzyme REST service and write the results to the SBML')
    parser.add_argument('-input', type=str)
    parser.add_argument('-input_format', type=str)
    parser.add_argument('-output', type=str)
    parser.add_argument('-weight_rule_score', type=float)
    parser.add_argument('-weight_fba', type=float)
    parser.add_argument('-weight_thermo', type=float)
    parser.add_argument('-weight_thermo_var', type=float)
    parser.add_argument('-weight_rp_steps', type=float)
    parser.add_argument('-max_rp_steps', type=int)
    parser.add_argument('-topX', type=int)
    parser.add_argument('-thermo_ceil', type=float)
    parser.add_argument('-thermo_floor', type=float)
    parser.add_argument('-fba_ceil', type=float)
    parser.add_argument('-fba_floor', type=float)
    parser.add_argument('-pathway_id', type=str)
    parser.add_argument('-objective_id', type=str)
    parser.add_argument('-thermo_id', type=str)
    params = parser.parse_args()
    if params.input_format=='tar':
        rpToolServe.main(params.input,
                         params.output,
                         params.topX,
                         params.weight_rp_steps,
                         params.weight_rule_score,
                         params.weight_fba,
                         params.weight_thermo,
                         params.weight_thermo_var,
                         params.max_rp_steps,
                         params.thermo_ceil,
                         params.thermo_floor,
                         params.fba_ceil,
                         params.fba_floor,
                         params.pathway_id,
                         params.objective_id,
                         params.thermo_id)
    elif params.input_format=='sbml':
        #make the tar.xz 
        with tempfile.temporarydirectory() as tmpoutputfolder:
            input_tar = tmpoutputfolder+'/tmp_input.tar.xz'
            output_tar = tmpoutputfolder+'/tmp_output.tar.xz'
            with tarfile.open(input_tar, mode='w:xz') as tf:
                #tf.add(params.input)
                info = tarfile.tarinfo('single.rpsbml.xml') #need to change the name since galaxy creates .dat files
                info.size = os.path.getsize(params.input)
                tf.addfile(tarinfo=info, fileobj=open(params.input, 'rb')) 
            rpToolServe.main(input_tar,
                             output_tar,
                             params.topX,
                             params.weight_rp_steps,
                             params.weight_rule_score,
                             params.weight_fba,
                             params.weight_thermo,
                             params.weight_thermo_var,
                             params.max_rp_steps,
                             params.thermo_ceil,
                             params.thermo_floor,
                             params.fba_ceil,
                             params.fba_floor,
                             params.pathway_id,
                             params.objective_id,
                             params.thermo_id)
            with tarfile.open(output_tar) as outtar:
                outtar.extractall(tmpoutputfolder)
            out_file = glob.glob(tmpoutputfolder+'/*.rpsbml.xml')
            if len(out_file)>1:
                logging.warning('there are more than one output file...')
            shutil.copy(out_file[0], params.output)
    else:
        self.logging('cannot identify the input_format: '+str(params.input_format))