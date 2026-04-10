import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge # so we can start programming rings/arcs 
import sys # for reading kotlin code

# get arguments, path and where infographic should be saved

#path = sys.argv[1]
#infographicPath = sys.argv[2]

# create infographic
fig,axes = plt.subplots()


# ring
green = "#008000"
orange = "#FFA500"
red = "#FF0000"
ringColour = green # can insert logic of how to pick the colour later
ring = Wedge(center=(0.5,0.5),r=0.25,theta1 = 0, theta2 = 90, width = 1, facecolor = ringColour)

# circle 
infographicCircle = plt.Circle((0.5,0.5),0.5, color = "#225382") # stroomloop blue

# readings in the centre of the circle
ax.text(0.6)

axes.set_aspect(1) # so circle doesnt become an oval
axes.add_patch(infographicCircle) # circle not drawn until attached to axis
plt.savefig("Infographiccircle.png")
plt.show()