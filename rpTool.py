#!/usr/bin/env python3

import libsbml
import sys
import logging
from scipy import stats
import numpy as np
import json

sys.path.insert(0, '/home/')
import rpSBML


## Normalise by sigmoidal function
# NOT USED
#
def nonlin(x,deriv=False):
    if(deriv==True):
        return x*(1-x)
    return 1/(1+np.exp(-x))



## Extract the reaction SMILES from an SBML, query rule_score and write the results back to the SBML
#
# Higher is better
#
# NOTE: all the scores are normalised by their maximal and minimal, and normalised to be higher is better
# Higher is better
#TODO: try to standardize the values instead of normalisation.... Advantage: not bounded
def calculateGlobalScore_json(rpsbml_json,
                              weight_rp_steps=0.002930832356389215,
                              weight_rule_score=0.14947245017584998,
                              weight_fba=0.5890973036342322,
                              weight_thermo=0.25849941383352876,
                              max_rp_steps=15, #TODO: add this as a limit in RP2
                              thermo_ceil=5000.0,
                              thermo_floor=-5000.0,
                              fba_ceil=5.0,
                              fba_floor=0.0,
                              pathway_id='rp_pathway',
                              objective_id='obj_fraction',
                              thermo_id='dfG_prime_m'):
    path_norm = {}
    ####################################################################################################### 
    ########################################### REACTIONS #################################################
    ####################################################################################################### 
    #WARNING: we do this because the list gets updated
    logging.info('thermo_ceil: '+str(thermo_ceil))
    logging.info('thermo_floor: '+str(thermo_floor))
    logging.info('fba_ceil: '+str(fba_ceil))
    logging.info('fba_floor: '+str(fba_floor))
    list_reac_id = list(rpsbml_json['reactions'].keys())
    for reac_id in list_reac_id:
        list_bd_id = list(rpsbml_json['reactions'][reac_id]['brsynth'].keys())
        for bd_id in list_bd_id:
            ####### Thermo ############
            #lower is better -> -1.0 to have highest better
            #WARNING: we will only take the dfG_prime_m value
            if bd_id[:4]=='dfG_':
                if bd_id not in path_norm:
                    path_norm[bd_id] = []
                try:
                    if thermo_ceil>=rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']>=thermo_floor:
                        #min-max feature scaling
                        norm_thermo = (rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']-thermo_floor)/(thermo_ceil-thermo_floor)
                        norm_thermo = 1.0-norm_thermo
                    elif rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']<thermo_floor:
                        norm_thermo = 1.0
                    elif rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']>thermo_ceil:
                        norm_thermo = 0.0
                except (KeyError, TypeError) as e:
                    logging.warning('Cannot find the thermo: '+str(bd_id)+' for the reaction: '+str(reac_id))
                    norm_thermo = 1.0
                rpsbml_json['reactions'][reac_id]['brsynth']['norm_'+bd_id] = {}
                rpsbml_json['reactions'][reac_id]['brsynth']['norm_'+bd_id]['value'] = norm_thermo
                logging.info(str(bd_id)+': '+str(rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value'])+' ('+str(norm_thermo)+')')
                path_norm[bd_id].append(norm_thermo)
            ####### FBA ##############
            #higher is better
            #return all the FBA values
            #------- reactions ----------
            elif bd_id[:4]=='fba_':
                try:
                    norm_fba = 0.0
                    if fba_ceil>=rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']>=fba_floor:
                        #min-max feature scaling
                        norm_fba = (rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']-fba_floor)/(fba_ceil-fba_floor)
                    elif rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']<=fba_floor:
                        norm_fba = 0.0
                    elif rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']>fba_ceil:
                        norm_fba = 1.0
                    rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value'] = norm_fba
                except (KeyError, TypeError) as e:
                    norm_fba = 0.0
                    logging.warning('Cannot find the objective: '+str(bd_id)+' for the reaction: '+str(reac_id))
                rpsbml_json['reactions'][reac_id]['brsynth']['norm_'+bd_id] = {}
                rpsbml_json['reactions'][reac_id]['brsynth']['norm_'+bd_id]['value'] = norm_fba
            elif bd_id=='rule_score':
                if bd_id not in path_norm:
                    path_norm[bd_id] = []
                #rule score higher is better
                path_norm[bd_id].append(rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value'])
            else:
                logging.info('Not normalising: '+str(bd_id))
    ####################################################################################################### 
    ########################################### PATHWAY ###################################################
    ####################################################################################################### 
    ############### FBA ################
    #higher is better
    list_path_id = list(rpsbml_json['pathway']['brsynth'].keys())
    for bd_id in list_path_id:
        if bd_id[:4]=='fba_':
            norm_fba = 0.0
            if fba_ceil>=rpsbml_json['pathway']['brsynth'][bd_id]['value']>=fba_floor:
                #min-max feature scaling
                norm_fba = (rpsbml_json['pathway']['brsynth'][bd_id]['value']-fba_floor)/(fba_ceil-fba_floor)
            elif rpsbml_json['pathway']['brsynth'][bd_id]['value']<=fba_floor:
                norm_fba = 0.0
            elif rpsbml_json['pathway']['brsynth'][bd_id]['value']>fba_ceil:
                norm_fba = 1.0
            else:
                logging.warning('This flux event should never happen: '+str(rpsbml_json['pathway']['brsynth'][bd_id]['value']))
            rpsbml_json['pathway']['brsynth']['norm_'+bd_id] = {}
            rpsbml_json['pathway']['brsynth']['norm_'+bd_id]['value'] = norm_fba
    ############# thermo ################
    for bd_id in path_norm:
        if bd_id[:4]=='dfG_':
            rpsbml_json['pathway']['brsynth']['norm_'+bd_id] = {}
            rpsbml_json['pathway']['brsynth']['var_'+bd_id] = {}
            #here add weights based on std
            logging.info(str(bd_id)+': '+str(path_norm[bd_id]))
            rpsbml_json['pathway']['brsynth']['norm_'+bd_id]['value'] = np.average([np.average(path_norm[bd_id]), 1.0-np.std(path_norm[bd_id])], weights=[0.5, 0.5])
            #the score is higher is better - (-1 since we want lower variability)
            #rpsbml_json['pathway']['brsynth']['var_'+bd_id]['value'] = 1.0-np.var(path_norm[bd_id])
    ############# rule score ############
    #higher is better
    if not 'rule_score' in path_norm:
        logging.warning('Cannot detect rule_score: '+str(path_norm))
        rpsbml_json['pathway']['brsynth']['norm_'+bd_id] = {}
        rpsbml_json['pathway']['brsynth']['norm_'+bd_id]['value'] = 0.0
    else:
        rpsbml_json['pathway']['brsynth']['norm_'+bd_id] = {}
        rpsbml_json['pathway']['brsynth']['norm_'+bd_id]['value'] = np.average(path_norm[bd_id])
    ##### length of pathway ####
    #lower is better -> -1.0 to reverse it
    norm_steps = 0.0
    if len(rpsbml_json['reactions'])>max_rp_steps:
        logging.warning('There are more steps than specified')
        norm_steps = 0.0
    else:
        try:
            norm_steps = (float(len(rpsbml_json['reactions']))-1.0)/(float(max_rp_steps)-1.0)
            norm_steps = 1.0-norm_steps
        except ZeroDivisionError:
            norm_steps = 0.0
    #################################################
    ################# GLOBAL ########################
    #################################################
    rpsbml_json['pathway']['brsynth']['norm_steps'] = {}
    rpsbml_json['pathway']['brsynth']['norm_steps']['value'] = norm_steps
    logging.info('Using the following values for the global score:')
    logging.info('Rule Score: '+str(rpsbml_json['pathway']['brsynth']['norm_rule_score']['value']))
    logging.info('Thermo: '+str(rpsbml_json['pathway']['brsynth']['norm_'+str(thermo_id)]['value']))
    logging.info('Steps: '+str(rpsbml_json['pathway']['brsynth']['norm_steps']['value']))
    logging.info('FBA ('+str('norm_fba_'+str(objective_id))+'): '+str(rpsbml_json['pathway']['brsynth']['norm_fba_'+str(objective_id)]['value']))
    ##### global score #########
    try:
        globalScore = np.average([rpsbml_json['pathway']['brsynth']['norm_rule_score']['value'],
                                  rpsbml_json['pathway']['brsynth']['norm_'+str(thermo_id)]['value'],
                                  rpsbml_json['pathway']['brsynth']['norm_steps']['value'],
                                  rpsbml_json['pathway']['brsynth']['norm_fba_'+str(objective_id)]['value']],
                                  weights=[weight_rule_score, weight_thermo, weight_rp_steps, weight_fba]
                                 )
        '''
        globalScore = (rpsbml_json['pathway']['brsynth']['norm_rule_score']['value']*weight_rule_score+
                       rpsbml_json['pathway']['brsynth']['norm_'+str(thermo_id)]['value']*weight_thermo+
                       rpsbml_json['pathway']['brsynth']['norm_steps']['value']*weight_rp_steps+
                       rpsbml_json['pathway']['brsynth']['norm_fba_'+str(objective_id)]['value']*weight_fba
                       )/sum([weight_rule_score, weight_thermo, weight_rp_steps, weight_fba])
        '''
    except ZeroDivisionError:
        globalScore = 0.0
    except KeyError as e:
        logging.error(rpsbml_json['pathway']['brsynth'].keys())
        logging.error('KeyError for :'+str(e))
        globalScore = 0.0
    rpsbml_json['pathway']['brsynth']['global_score'] = {}
    rpsbml_json['pathway']['brsynth']['global_score']['value'] = globalScore
    return globalScore

################################################################################
################################## HANDLE RPSBML ###############################
################################################################################

def calculateGlobalScore_rpsbml(rpsbml,
                                weight_rp_steps,
                                weight_rule_score,
                                weight_fba,
                                weight_thermo,
                                max_rp_steps=15, #TODO: add this as a limit in RP2
                                thermo_ceil=5000.0,
                                thermo_floor=-5000.0,
                                fba_ceil=5.0,
                                fba_floor=0.0,
                                pathway_id='rp_pathway',
                                objective_id='obj_fraction',
                                thermo_id='dfG_prime_m'):
    rpsbml_json = rpsbml.genJSON(pathway_id)
    globalscore = calculateGlobalScore_json(rpsbml_json,
                                            weight_rp_steps,
                                            weight_rule_score,
                                            weight_fba,
                                            weight_thermo,
                                            max_rp_steps,
                                            thermo_ceil,
                                            thermo_floor,
                                            fba_ceil,
                                            fba_floor,
                                            pathway_id,
                                            objective_id,
                                            thermo_id)
    updateBRSynthPathway(rpsbml, rpsbml_json, pathway_id)
    return globalscore


def updateBRSynthPathway(rpsbml, rpsbml_json, pathway_id='rp_pathway'):
    logging.info('rpsbml_json: '+str(rpsbml_json))
    groups = rpsbml.model.getPlugin('groups')
    rp_pathway = groups.getGroup(pathway_id)
    for bd_id in rpsbml_json['pathway']['brsynth']:
        if bd_id[:5]=='norm_' or bd_id=='global_score':
            try:
                value = rpsbml_json['pathway']['brsynth'][bd_id]['value']
            except KeyError:
                logging.warning('The entry '+str(db_id)+' doesnt contain value')
                logging.warning('No" value", using the root')
            try:
                units = rpsbml_json['pathway']['brsynth'][bd_id]['units']
            except KeyError:
                units = None
            rpsbml.addUpdateBRSynth(rp_pathway, bd_id, value, units, False)
    for reac_id in rpsbml_json['reactions']:
        reaction = rpsbml.model.getReaction(reac_id)
        if reaction==None:
            logging.warning('Skipping updating '+str(reac_id)+', cannot retreive it')
            continue
        for bd_id in rpsbml_json['reactions'][reac_id]['brsynth']:
            if bd_id[:5]=='norm_':
                try:
                    value = rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['value']
                except KeyError:
                    value = rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]
                    logging.warning('No" value", using the root')
                try:
                    units = rpsbml_json['reactions'][reac_id]['brsynth'][bd_id]['units']
                except KeyError:
                    units = None
                rpsbml.addUpdateBRSynth(reaction, bd_id, value, units, False)
