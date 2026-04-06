# PICTUS

![lab_logo](https://github.com/user-attachments/assets/6ae06c25-0459-4676-a054-f8e9962b4b88)

Created by the [Hamdoun lab at the Scripps Institution of Oceanography](https://www.hamdounlab.org).

PICTUS (Positional Identification and Continuous Tracking of Urchin Subjects) is a computer vision-based algorithm designed to autonomously track the 3D location of a painted sea urchin, L. pictus, within a lab-based tank. This repository contains:

a) A YOLOv12n model trained to recognize roving L. pictus.

b) A series of scripts that apply this model to live footage collected on a Raspberry Pi 5's Camera Module 3 Wide and convert 2D positional bounding boxes into a 3D space.

c) Instructions on how to use the above scripts so you can perform live inference of your own.

d) 3D printer-ready .stl files of the lid and custom tank used in our lab. Note that this system can be adapted to any configuration: you just need to have two Camera Module 3s.

Before beginning, make sure you have obtained the following:

a) Raspberry Pi 5 (x4). You can format each of the Pis using the Raspberry Pi Imager. During formatting, you will want to install the Raspberry Pi OS (Legacy, 64-bit) containing a port of Debian Bookworm. Installing the wrong OS can cause several of the packages used by this code to break.

b) Camera Module 3 (x2). You will want to install one of the Camera Module 3 units per Raspberry Pi. Two of the Pis should have attached Camera Module 3s and two will not. From this point onward, the two Pis with the Camera Module 3 units will be referred to as the remote Pis while the two Pis without the Camera Module 3 units will be referred to as the local Pis.

c) On both remote Pis, create a virtual environment using `python3 -m venv –system-site-packages venv` on the command line. Within your venv, install pip and Ultralytics via `python -m pip install -U pip` and `python -m pip install ultralytics`. Then, still within your venv, uninstall numpy via `python -m pip uninstall numpy`.

You are now ready to begin using PICTUS.
