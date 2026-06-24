# PICTUS

![lab_logo](https://github.com/user-attachments/assets/6ae06c25-0459-4676-a054-f8e9962b4b88)

Created by the [Hamdoun lab at the Scripps Institution of Oceanography](https://www.hamdounlab.org).

PICTUS (Positional Identification and Continuous Tracking of Urchin Subjects) is a computer vision-based algorithm designed to autonomously track the 3D location of a painted sea urchin, L. pictus, within a lab-based tank. This repository contains:

a) A YOLOv12n model trained to recognize roving L. pictus.

b) A series of scripts that apply this model to live footage collected on a Raspberry Pi 5's Camera Module 3 Wide and convert 2D positional bounding boxes into a 3D space.

c) Instructions on how to use the above scripts so you can perform live inference of your own.

d) 3D printer-ready .3mf files of the lid and custom tank used in our lab. Note that this system can be adapted to any configuration: you just need to have two Camera Module 3s.

============================================================================

Before beginning, make sure you have obtained the following:

a) Raspberry Pi 5 (x4). You can format each of the Pis using the Raspberry Pi Imager. During formatting, you will want to install the Raspberry Pi OS (Legacy, 64-bit) containing a port of Debian Bookworm. Installing the wrong OS can cause several of the packages used by this code to break.

b) Camera Module 3 (x2). You will want to install one of the Camera Module 3 units per Raspberry Pi. Two of the Pis should have attached Camera Module 3s and two will not. From this point onward, the two Pis with the Camera Module 3 units will be referred to as the remote Pis while the two Pis without the Camera Module 3 units will be referred to as the local Pis.

c) Physical mount for your cameras. You can either 3D print the mounts used by our lab by referencing the attached .3mf files or design your own. You will want to make sure that both Camera Module 3 units are mounted such that they can see the urchin you are tracking.

d) Arduino Nano Every (x1), breadboard (x1), and appropriate wiring. You will be wiring the Arduino to the local Pis using the below diagram. You will follow this same wiring process for every local Pi you attach to the Arduino:

<img width="287" height="470" alt="wiringDiagram" src="https://github.com/user-attachments/assets/1fea22ef-ca4f-4273-9419-e5f66fdacf68" />

It is particularly important that both Pis are connected to the Arduino via GPIO 17 (pin 11 on the Raspberry Pi 5).

============================================================================

Once you have obtained the necessary physical components, perform the following software setup steps:

a) On both remote Pis, create a virtual environment using `python3 -m venv –system-site-packages venv` on the command line. 

b) Within your venv, install pip and Ultralytics via `python -m pip install -U pip` and `python -m pip install ultralytics`. 

c) Then, still within your venv, uninstall numpy via `python -m pip uninstall numpy`.

d) Download **urchinCV.pt** from this repository onto all remote Pis.

e) Design and print out a calibration checkerboard from [this website](https://calib.io/pages/camera-calibration-pattern-generator?srsltid=AfmBOoq6vzACCUKuUx5DGQdfQGDeRlbra-3Hk-I1jseB0dcrQT10LPJQ). When designing the checkerboard, make sure that it has a different number of rows and columns and that it will be small enough such that it can be seen simultaneously from all cameras.

f) Mount your checkerboard on a rigid surface. It is important that the checkerboard is flat. If your cameras are oriented 180 degrees removed from one another, mount a checkerboard on each side of your rigid surface such that the two checkerboards are back-to-back.

g) Make sure that your cameras are oriented exactly as they will be when recording urchin movement. Place your mounted checkerboard between the cameras such that all checkerboard boxes are visible on all cameras. **Without moving the checkerboard,** take a photo from all cameras. It is essential that the checkerboard is in the exact same position across all photos. Once you have taken a photo of the checkerboard from all cameras, move the checkerboard and repeat. You will ultimately want approximately 30-50 sets of images of the checkerboard. The checkerboard's x, y, and z orientation should change between image sets such that it ultimately covers the entire 3D space your cameras will be recording. Do not rotate the checkerboard more than ~45 degrees.

h) Once you are happy with your image sets, collect them into several folders. Each folder should contain all images taken from one camera. Sets of images (i.e. the images taken from different cameras of the same checkerboard orientation) should have the same name. Run **scriptCalibration.py** to generate a set of transformation matrices. These matrices will later be used to convert your 2D points into 3D coordinates.

i) Note that, if you ever change the configuration of your cameras, you will need to repeat steps e-h.

You are now ready to begin using PICTUS.

============================================================================

1) Download **remoteDaemon.py** and **best.pt** onto your remote Pis, **localTrigger.py** onto your local Pis, and **arduinoPulse.ino** onto the device you will be using to trigger your synchronized recordings.

2) Check and record the IP addresses of all of your Pis using `hostname -I` from the command line. You will want to make sure that the network your Pis are connected to will allow you to maintain stable IP addresses.

3) Physically prepare your system for recording. Your local Pis will be wired to another device (any computer is fine, so long as it can run **Arduino IDE** and **arduinoPulse.ino**). Your remote Pis will be wherever you are recording.

4) Open your virtual environment on the remote Pis. Run **remoteDaemon.py** with `remoteDaemon.py --local-ip **IP OF THE LINKED LOCAL PI** --model-path **PATH TO urchinCV.pt** --capture-duration **LENGTH OF DESIRED RECORDING** --output-folder **LOCATION TO SAVE RECORDINGS AND BOUNDING BOXES TO**`. You should see the message: **Expected message: START**.

5) Run **localTrigger.py** with `localTrigger.py --remote-host **IP OF THE LINKED REMOTE PI** --remote-user **USERNAME ON LINKED REMOTE PI**`. You should see the message: **Waiting for Arduino pulse...**.

6) Run **arduinoPulse.ino**. This should immediately trigger the message **Pulse at TIME. Sent firing key at TIME.** on your local Pis and the message **Starting recording.** on your remote Pis.

7) Once the designated recording time as passed, you will see the following message on your remote Pis: **Finished recording. Press Ctrl + C to stop the program.** When the recording finishes, a video of the recording (containing bounding boxes) and a .csv file containing the coordinates of the bounding box(es) from each frame will be saved at the location designated in step 4.

8) Move the .csv files containing the bounding box coordinates from both remote Pis onto the same computer which contains your stereo matrices from above. Run **script2DTo3D.py**, making sure to first edit the paths within the script appropriately. This will generate a .csv file containing the 3D coordinates of your tracked urchin!
