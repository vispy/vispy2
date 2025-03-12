# Architecture

## Introduction

Interactive visualization of raw data is a fundamental tool in scientific research, enabling scientists to generate and explore hypotheses efficiently. As datasets continue to grow exponentially across disciplines, scalable computer tools are necessary for handling and visualizing large volumes of data in real time.

Modern Graphics Processing Units (GPUs) provide a powerful solution for scientific visualization. Originally developed for 3D video games, GPUs are optimized for parallel computing and can efficiently render complex visualizations. However, leveraging GPUs for scientific visualization requires specialized techniques and software architectures.

## The original VisPy project

The **VisPy** project was initiated in 2013 by four developers: **Luke Campagnola, Almar Klein, Cyrille Rossant, and Nicolas Rougier**. It aimed to provide a high-performance interactive scientific visualization toolkit based on **OpenGL**. While VisPy gained traction within the scientific community, its reliance on OpenGL introduced significant limitations:

- **OpenGL is aging**: OpenGL has been somewhat replaced by newer APIs such as Vulkan, Metal, and WebGPU.
- **Technical debt**: Maintaining compatibility with modern GPUs while relying on OpenGL has become increasingly difficult.
- **Lack of scalability**: OpenGL does not fully leverage modern GPU capabilities, leading to performance bottlenecks in large-scale visualizations.

## The need for a new architecture

GPU graphics APIs evolve rapidly, making it difficult for scientific developers to keep up with the latest technologies. However, the **high-level plotting interfaces** used by scientists remain relatively stable over time. This discrepancy presents a challenge: if the architecture intertwines high-level plotting with low-level rendering, then every major graphics API shift requires a full rewrite of the visualization library.

To address this challenge, **Nicolas Rougier and Cyrille Rossant** envision a new architecture centered around the **Graphics Server Protocol (GSP)**. The fundamental idea behind GSP is:

- **The core GPU-based rendering technology is a moving target**, while
- **The high-level scientific plotting interfaces are much more stable** and easier to maintain.

By **decoupling high-level visualization from low-level rendering**, we ensure that only the low-level part of the system needs to be updated when graphics APIs evolve. This allows VisPy 2.0 to remain relevant over time, adapting to new GPU technologies with minimal effort.

## Graphics Server Protocol (GSP)

GSP defines a common framework for representing scientific visualizations **agnostic to the underlying GPU technology**. Instead of directly interfacing with OpenGL, Vulkan, Metal, or WebGPU, VisPy 2.0 will communicate with a GSP-compatible graphics engine.

### Key features of GSP

- **Unified Visual Object Model**: GSP defines a small, predefined set of fundamental visual types (e.g., markers, lines, meshes, images, text).
- **Asynchronous Rendering**: GSP is a simple, asynchronous protocol where clients send visualization commands to a rendering server.
- **Remote and Distributed Rendering**: The rendering machine can be separate from the data server, allowing for scalable cloud-based visualization.

### Specification of GSP

An advanced draft of the specification will be released in March 2025 in a separate repository, along with many examples.

### Implementation of GSP

Currently, GSP has two primary implementations:

- **Matplotlib-Based Implementation**: A slow but functional implementation for testing and rapid prototyping.
- **Datoviz Implementation**: A high-performance, Vulkan-based rendering engine designed to match GSP.

[Datoviz](https://datoviz.org) is a **C/C++ Vulkan-based** graphics engine specifically designed for scientific visualization. Unlike traditional graphics engines optimized for video games, Datoviz prioritizes:

- **Scalability to massive datasets**
- **High-quality GPU-accelerated 2D and 3D rendering**
- **Minimal overhead, leveraging modern GPU capabilities**

The Datoviz user API has been designed in parallel with GSP so as to match it as much as possible. The GSP-Datoviz bridge is still development but it will be lightweight and share components with the Matplotlib-based implementation.

## The high-Level plotting API

The next major step for VisPy 2.0 is designing a user-friendly scientific plotting API on top of GSP. This API must balance:

- **Performance** (leveraging GPU acceleration)
- **Simplicity** (easy to use for scientists)
- **Scalability** (handling large datasets efficiently)

The first priority is defining a **"good enough" API** that covers the most common use cases in 2D and 3D visualization. Community feedback will be critical in shaping this API.

### Proposed high-level API design

We propose a **Python-based** object-oriented interface where users define figures, panels, and visualization objects.

#### **Core objects**

- `Figure`: Represents a desktop window with width and height.
- `Panel`: A subplot within a figure, defined by its position and size.
- `Camera`: A 3D camera (e.g., trackball control for rotation).
- `Axis`: 2D axes in a panel with pan and zoom functionality.

#### **Basic Visual Primitives**
##### **2D Objects**
- `Disc`
- `Square`
- `Triangle`

##### **3D Objects**
- `Sphere`
- `Cube`
- `Cylinder`
- `Cone`

#### **Plotting Objects**
##### **2D Plots**
- `Scatter`
- `Image`
- `Text`
- `Barplot`
- `Segment`
- `Path`
- `Polygon`

##### **3D Plots**
- `Mesh`
- `Volume`
- `Slice`

####

These objects have attributes (position, color, size...) that can be dynamically updated, resulting in the automatic generation of GSP commands that are sent to the underlying renderer (typically, Datoviz, which will convert them into Vulkan update commands for the GPU).

Toy example:

```python
import vispy2 as vp

fig = vp.Figure(800, 600)
x = ...
y = ...
color = ...
s = vp.Scatter(x, y, color=color, fig=fig)
vp.run()
```


### Performance considerations

A key feature of VisPy 2.0 is its ability to efficiently handle **thousands or millions of individual objects**. Unlike traditional approaches where every object incurs overhead, VisPy 2.0 will **automatically batch similar objects** for rendering efficiency. This is crucial for GPU performance, as modern graphics pipelines excel at rendering **large batches of similar primitives**.

## Community involvement

The API proposal above is just a **starting point**. We actively seek feedback from the community on:

- **Common use cases** that should be prioritized
- **Missing functionality** or limitations in the proposed design
- **Best practices for usability and extensibility**

We encourage discussions and contributions in this repository.


## Conclusion

VisPy 2.0 represents a major leap forward in GPU-based scientific visualization by:

- **Separating high-level visualization from low-level rendering**
- **Leveraging GSP to future-proof the architecture**
- **Enabling scalable, high-performance rendering for large datasets**
- **Providing an intuitive, Pythonic API for scientific users**

We look forward to engaging with the community to refine and enhance this new architecture. Feedback and contributions are highly encouraged!
