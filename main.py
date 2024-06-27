import os
import sys
import pickle
from tqdm import tqdm

import meep as mp
import matplotlib.pyplot as plt
from IPython.display import Video, display
import cv2
import numpy as np

from utils.update_config import update as update_config
from utils.helpers import load_config, is_mpi_run, delete_outputs, create_folder
from utils.visualizations import display_fields, display_video, display_chars, animate, combine_subplots
from utils.build_sim import build_sim

from IPython import embed

until = 200

def run_experiment(params, geometry, sources, sim, flux_region, flux_object):

 
    ## Initial run without pillars
    sim.run(until=until)

    ## Save image of fields propagating without pillars
    display_fields(params, sim, rad=0)

    initial_flux = mp.get_fluxes(flux_object)[0]  # flux through substrate and PDMS - no pillar  

    ## Important to reset meep before we update the simulation with new geometry      
    sim.reset_meep()

    ## We'll use this to collect transmission and phase info for each pillar radius 
    data = np.zeros((3,params['experiment']['num']))

    ## progress bar for convenience - keeps us updated on how many sims we have left to run
    pbar = tqdm(total=params['experiment']['num'],leave=False)

    ## need to make a list of radii. the parameter, experiment.num from the config file determines
    ## how many radii we'll generate
    radii = np.linspace(params['amorphousSi']['radius_min'],
                        params['amorphousSi']['radius_max'],
                        num=params['experiment']['num'])

    ## launch sims for each radius in `radii` - collect phase and transmission info
    for i,radius in enumerate(radii):

        geometry.append(mp.Cylinder(radius=radius,
                            height=params['amorphousSi']['height'],
                            axis=mp.Vector3(0,0,1),
                            center=mp.Vector3(0,0,params['amorphousSi']['center']),
                            material=mp.Medium(index=params['amorphousSi']['n'])))
    
        sim = mp.Simulation(cell_size=params['cell_size'],
                            geometry=geometry,
                            sources=sources,
                            k_point=params['k_point'],
                            boundary_layers=params['pml']['layers'],
                            symmetries=params['symmetries'],
                            resolution=params['resolution'])
        
        flux_object = sim.add_flux(params['freq'], params['flux']['df'],
                                   params['flux']['nfreq'], flux_region)  
    
        sim.run(until=until)

        display_fields(params, sim, radius)

        res = sim.get_eigenmode_coefficients(flux_object, [1], eig_parity=mp.ODD_Y)
        coeffs = res.alpha
         
        flux = abs(coeffs[0,0,0]**2)
        phase = np.angle(coeffs[0,0,0]) 
       
        data[0,i] = radius
        data[1,i] = flux / initial_flux 
        data[2,i] = phase
         
        if radius < params['amorphousSi']['radius_max']:
            sim.reset_meep()
            geometry.pop()

        pbar.update(1)
    
    pbar.close()

    return data, sim
    
if __name__=="__main__":

    ## load in parameters from the command line argument and apply them to configs.yaml
    params = load_config(sys.argv)

    ## update parameters that require math (yaml files can't do math)
    params = update_config(params)

    ## build simulation using custom file imported above (build_sim.py) 
    geometry, sources, sim, flux_region, flux_object = build_sim(params)

    ## this is the location where we'll store images and movies
    rel_path = 'vis'
    abs_path = os.path.abspath(rel_path)
    create_folder(abs_path)


    ## This runs a single simulation and builds a video of waves propagating through a single pillar
    ## Do not use mpirun when executing this.
    if params['experiment']['animate'] == 1:

        if is_mpi_run():

            print("Error: MPI detected. Please do not use mpirun to generate animations.")         
            sys.exit(1)

        else:

            print("problem")

        radius = 0.1625
        geometry.append(mp.Cylinder(radius=radius,
                            height=params['amorphousSi']['height'],
                            axis=mp.Vector3(0,0,1),
                            center=mp.Vector3(0,0,params['amorphousSi']['center']),
                            material=mp.Medium(index=params['amorphousSi']['n'])))

        sim = mp.Simulation(cell_size=params['cell_size'],
                            geometry=geometry,
                            sources=sources,
                            k_point=params['k_point'],
                            boundary_layers=params['pml']['layers'],
                            symmetries=params['symmetries'],
                            resolution=params['resolution'])

       
        video_path = f"vis/animation_radius_{radius}.mp4"
        animate(params, sim, geometry, radius, video_path)        
        display_video(video_path)


    ## This launches the experiment and generates analysis:
    ## --- 1. phase/transmission characteristics curve as a .png
    ## --- 2.     
    elif params['experiment']['animate'] == 0:

        print(params['experiment']['animate'])
        print()

        # This is going to generate a .png image for each simulation corresponding to number
        # of radii (set in config file, experiment.num
        data, sim = run_experiment(params, geometry, sources, sim, flux_region, flux_object)

        # This combines all of the images so you can observe the phase delay as pillar radius
        # increases. This plot will pop up as the code executes.
        combine_subplots()

        # This plots the phase and transmission with respect to radius. 
        display_chars(params, data) 

        delete_outputs(params) # comment this line if you want to preserve the output files

        # we're not using this, but just want to demonstrate how meep outputs epsilon data, 
        # which representes the materials/geometry.
        eps_data = sim.get_epsilon()

    else:
        raise NotImplementedError 

