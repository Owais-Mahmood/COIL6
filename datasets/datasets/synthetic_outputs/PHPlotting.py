import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge # so we can start programming rings/arcs 
import sys # for reading kotlin code

# get arguments, path and where infographic should be saved

#path = sys.argv[1]
#infographicPath = sys.argv[2]

# create infographic
fig,axes = plt.subplots()

# circle 
infographicCircle = plt.Circle((0.5,0.5),0.5, color = "#225382") # stroomloop blue
axes.add_patch(infographicCircle)

# ring
green = "#008000"
orange = "#FFA500"
red = "#FF0000"
ringColour = green # can insert logic of how to pick the colour later
ring = Wedge(center=(0.5,0.5),r=0.25,theta1 = 0, theta2 = 90, width = 0.1, facecolor = ringColour)
axes.add_patch(ring)

# readings in the centre of the circle
axes.text(0.5, 0.5,"LIVE READING", ha = 'center', va = 'center', fontsize = 15, color = 'white')
axes.text(0.5,0.5,"pH Scale", ha = 'center', va = 'center', fontsize = 10, color = 'white')

# status
normal = "normal"
moderate = "moderate"
critical = "critical"
status = normal # add code here to decide what critical level it is = insert logic
axes.text(0.5,0.25,status,ha = 'center', va = 'center', fontsize = 13, color = 'white')

# timestamp
####### insert code

# organising data
axes.set_aspect(1) # so circle doesnt become an oval
axes.set_xlim(0,1) # so ring is shown
axes.set_ylim(0,1) # so ring is shown
axes.axis("off")

# create image
plt.savefig("Infographiccircle.png")
plt.show()