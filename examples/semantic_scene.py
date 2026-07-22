"""Build and inspect a VisPy2 scene without installing a backend."""

import vispy2 as vp


figure, axes = vp.subplots()
axes.set_title("Backend-neutral scene")
axes.set_xlabel("x")
axes.set_ylabel("y")
axes.scatter([-0.7, 0.0, 0.7], [-0.3, 0.4, -0.1], size=[18.0, 32.0, 24.0])

scene = figure.to_scene()

if __name__ == "__main__":
    print(scene)
