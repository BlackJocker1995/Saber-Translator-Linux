# Seber-Translator-linux

Self-use version adapted for Linux; after installing the necessary dependencies, you can run it with python app.py.


## requirement
1. 'sd-webui-cleaner' dir from original project's release package.
2. 'ultralytics_yolov5_master' dir from original project's release package.
3. 'weights' dir from from original project's release package.
4. Pytorh

## change
1. WebP is used as the default intermediate storage medium globally to save cache space.
2. Added the tag qwen no_think
3. In order to read the YOLO files trained by the original project on Windows, this program forcibly uses Path conversion. 
It is currently unclear whether any bugs will occur.
4. Fix an issue with image transmission; the transmission header should be determined based on the image format of the source file rather than hardcoding PNG.