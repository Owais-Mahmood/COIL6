import pandas as pd
import matplotlib.pyplot as plt 
from matplotlib.patches import Wedge # so we can start programming rings/arcs 
import sys
import os

csv_path = sys.argv[1]

output_path = sys.argv[2]

def waterLevel_loading(csv_path: str):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    return df[['timestamp', 'site_id', 'water_level_cm']]

def ring_creation(axes, value, min_value, max_value, site_id, timestampStr):
    if value < 50.0 or value>750.0:
        ringColour = "#FF0000"
    elif value<=50.0 and value>=600.0:
        ringColour = "#FFFB00"
    elif value>50.0 and value<600.0:
        ringColour = "#0FFF0F"
    
        #ringColour = "#FFF700FF" research moderate

    #circle 
    infographicCircle = plt.Circle((0.5,0.5),0.5, color = "#22548200") # stroomloop blue
    axes.add_patch(infographicCircle) # circle not drawn until attached to axis

    # arc logic - percentage change
    percentage = (value-min_value)/(max_value-min_value)
    percentage = max(0.0,min(1.0,percentage)) # making sure percentage is between 0 and 1

    # changing fraction to degrees to show on ring
    maxRing = 360
    arc = percentage * maxRing
    ring = Wedge(center=(0.5,0.5),r=0.5,theta1 = 90, theta2 = (90-arc), width = 0.11, facecolor = ringColour) # note: matplotlib draws ring anti-clockwise? could this be a probelm with arcs we need to fix
    axes.add_patch(ring)
    
    #readings in the centre of the circle
    axes.text(0.5, 0.55, f"{value}", ha = 'center', va = 'center', fontsize = 28, color = "#FFFFFF") # note change back to white
    axes.text(0.5,0.45,"cm", ha = 'center', va = 'center', fontsize = 18, color = "#FFFFFF")

    # status
    if value < 50.0 or value>750.0:
        status = "critical"
    elif value<=50.0 and value>=600.0:
        status = "moderate"
    elif value>50.0 and value<600.0:
        status = "healthy"
        
    axes.text(0.5,0.25,status,ha = 'center', va = 'center', fontsize = 14, color = "#FFFFFF") # note change back to white this is just for testing

    #site title
    axes.set_title(site_id, fontsize=16, color="#FFFFFF", fontweight = 'bold') #make white later
    #timestamp 
    axes.text(0.5, 0.35, timestampStr, ha='center', va='center', fontsize=14, color= "#FFFFFF")
        

    # organising data
    axes.set_aspect(1) # so circle doesnt become an oval
    axes.set_xlim(0,1) # so ring is shown
    axes.set_ylim(0,1) # so ring is shown
    axes.axis("off")
    print(f"{site_id}: value={value}, pct={percentage}, arc={arc}")

def plot_recent_reading(df: pd.DataFrame, output_dir: str):
    recentReading = df.sort_values('timestamp').groupby('site_id').last().reset_index()     #getting most recent reading

    site_ids = list(recentReading ['site_id'])
    values = list(recentReading ['water_level_cm'])
    timestamps = list(recentReading ['timestamp'])

    os.makedirs(output_dir, exist_ok=True)

    for i in range(len(site_ids)):
        #changing format of timestamp to be more pretty
        timestampStr = timestamps[i].strftime('%Y-%m-%d %H:%M')
        
        fig, ax = plt.subplots(1, 1)
        ring_creation(ax, values[i], min_val, max_val, site_ids[i], timestampStr)

        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)
        out_path = os.path.join(output_dir, f"waterLevel_{site_ids[i]}.png")
        fig.savefig(out_path, dpi=150, bbox_inches='tight', transparent=True)
        plt.close(fig)  #Free memory important when generating many plots in one run
        print(f"Saved: {out_path}")


df = waterLevel_loading(csv_path)
#range of readings from csv file
min_val, max_val = 0.0, df['water_level_cm'].max()
plot_recent_reading(df, output_path)