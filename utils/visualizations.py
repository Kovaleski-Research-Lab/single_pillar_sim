import meep as mp
import matplotlib.pyplot as plt
from IPython.display import Video, display
import numpy as np
import cv2
import re
import os
from PIL import Image

def create_folder(path):

    if not os.path.exists(path):
        os.makedirs(path)

    else:
        print(f"path {path} already exists.")

def get_colors(num_colors):

    cmap_viridis = plt.cm.get_cmap('viridis')
    colors = [cmap_viridis(i / num_colors) for i in range(num_colors)]

    return colors

def display_fields(params, sim, rad):

    ## If you want to see the geometry without the fields, remove the second parameter
    ## of sim.plot2D

    plt.figure(figsize=(5,8))
    plot_plane = mp.Volume(center=mp.Vector3(0,0.0*params['cell']['y'], 0),
                            size=mp.Vector3(params['cell']['x'], 0, params['cell']['z']))
    sim.plot2D(output_plane=plot_plane, fields=params['source']['cmpt'])
    plt.title(f"Fields at radius = {rad:.3f} micron")
    plt.savefig(f'vis/fields_{rad:.3f}.png')

    if mp.am_master():
    #    plt.show()
        plt.close("all")


def combine_subplots():

    dir_path = os.listdir("vis")
    radii = []
    image_files = []

    pattern = re.compile(r'fields_(\d+\.\d+)\.png')

    for f in dir_path:

        if f.endswith(".png"):
       
            image_files.append(f)
 
            match = pattern.match(f)
            if match:
                # Extract the number and convert it to an integer
                num = float(match.group(1))
                # Append the number to the list
                radii.append(num) 

    radii.sort()
    image_files.sort()

    fig, ax = plt.subplots(1, len(radii), figsize=(4*len(radii), 8))

    for axis, image_file in zip(ax, image_files):

        image = Image.open(os.path.join("vis",image_file))
        axis.imshow(image)
        axis.axis('off')
        
    plt.tight_layout()

    plt.show()


def mod_axes(ax, rad):

    font = {'fontsize': 12}
    
    ax.set_xlabel('X [$\mu$m]', fontdict=font)
    ax.set_ylabel('Z [$\mu$m]', fontdict=font)
    ax.tick_params(axis='both', labelsize=14)
    ax.set_title(f'Rad = {rad}')

    return ax

def animate(params, sim, geometry, radius, video_path):
    
    plot_plane = mp.Volume(center=mp.Vector3(0,0.0*params['cell']['y'],0),
                            size=mp.Vector3(params['cell']['x'],0,params['cell']['z']))
    
    plot_modifiers = [lambda ax: mod_axes(ax, radius)]

    f = plt.figure(dpi=100, figsize=(5,8))
    Animate = mp.Animate2D(output_plane=plot_plane, fields=params['source']['cmpt'],
                           f=f, realtime=False, normalize=True, plot_modifiers=plot_modifiers)

    sim.run(mp.at_every(0.1, Animate), until=25)

    Animate.to_mp4(params['vis']['fps'], video_path)

    plt.close(f)

def display_video(video_file):

    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():

        print(f"Error: Could not open video file {video_file}")
        return
    while cap.isOpened():

        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Video', frame)

        # Press 'q' to exit the video playback
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()    
    

def display_chars(params, data):

    radii = data[0]
    flux_list = data[1]
    phase_list = data[2] 

    print("display chars func")
    plt.style.use('seaborn-v0_8')
    
    tickfontsize=12
    labelfontsize=14
    titlefontsize=20

    colors = get_colors(2)

    fig,ax = plt.subplots(figsize=(8,5)) 
    
    fig.suptitle("Meta-atom Characteristics",fontsize=titlefontsize)
    
    ax.set_xlabel("Radius (nm)",fontsize=labelfontsize)
    ax.set_xlim([0.07, 0.26])
    ax.set_xticks([0.075, 0.100, 0.125, 0.150, 0.175, 0.200, 0.225, 0.250])
    ax.set_xticklabels([75, 100, 125, 150, 175, 200, 225, 250], fontsize=tickfontsize)
    ax.set_ylim([0, 1])
    ax.set_ylabel(r'Percent Transmitted ($\%$)', fontsize=labelfontsize, color=colors[0])
    ax.plot(radii, flux_list, color=colors[0], label='Transmission')
    ax.tick_params(axis='y', labelcolor=colors[0])
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=tickfontsize)
    
    twin1 = ax.twinx()
    
    twin1.set_xlim([0.07, 0.26])
    twin1.set_ylim([-np.pi, np.pi])
    twin1.set_ylabel(r'Phase Delay (rad)', fontsize=labelfontsize, color=colors[1])
    twin1.set_yticks([-np.pi, -(0.5*np.pi),0, np.pi / 2, np.pi])
    twin1.set_yticklabels([r'-$\pi$', r'-$\frac{\pi}{2}$', r'0', r'$\frac{\pi}{2}$', r'$\pi$'], fontsize=tickfontsize+4)
    twin1.plot(radii, phase_list, color=colors[1], label='Phase')
    twin1.tick_params(axis='y', labelcolor = colors[1])

    lines_labels = [ax.get_legend_handles_labels(), twin1.get_legend_handles_labels()]
    lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
    ax.legend(lines, labels, loc='best')
    
    if mp.am_master():
        plt.show()

    fig.savefig('vis/chars.png')
