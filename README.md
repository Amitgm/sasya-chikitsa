# sasya-chikitsa
An AI driven application to help farmers and plant enthusiasts identify plant diseases and get useful recommendations.


## Instructions and Pre-requisites for Buliding the App
Step 1 : Install Android Studio from developer.android.com.
Launch Android Studio → Create New Project → Empty Activity.
Choose:
Language: Kotlin
Minimum SDK: API 24+ (for camera/gallery access)
Finish project creation.
Open AVD Manager (Device Manager) → Create an Emulator.

 Steps to Create an Emulator
 1. Open Device Manager in the right side corner like Phone like Diagram.
 2. Click “+ Create Device”.
 3. Select a Pixel device (Pixel 7). 
 4. Choose a System Image (API 34 "UpsideDownCake"; Android 14.0). ( I have choosen Pixel and System Image Randomly)
 5.Download the system image if not installed.
 6. Name your emulator.
 7.Finish → Now you can run the emulator.


Step 2 : Update AndroidManifest.xml file with my code in app/src/main/java folder

Step 3 : Update activity_main.xml file with my code in app/src/main/res folder( This file should be in res/layout. If u don't find layout directory then create the Android Resource Directory and Rename it to layout and then create Android Resource File and rename it to activity_main.xml) 

Step 4 : Update MainActivity.kt file with my code in app/src/main/java folder

Step 5: Run on Emulator (Click Run Button on Top ) -- It will take 5-6 min to connect and Run the Emulator


## Instruction for running MADR on local

```bash
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v2.6.10
❯ chruby ruby-3.4.1
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v3.4.1
❯ ruby -v

ruby 3.4.1 (2024-12-25 revision 48d4efcb85) +PRISM [arm64-darwin24]
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v3.4.1
❯ clear
if [ /Users/rajranja/Documents/software/roxctl/roxctl ]; then
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v3.4.1
❯ vim ~/.zshrc
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v3.4.1 took 24s
❯ ruby -v

ruby 3.4.1 (2024-12-25 revision 48d4efcb85) +PRISM [arm64-darwin24]
sasya-chikitsa on  main [✘?] via  v8.13 via  v17.0.16 via  via  v3.13.6 via  v3.4.1
❯ gem install bundler jekyll
Successfully installed bundler-2.7.1
Successfully installed jekyll-4.4.1
2 gems installed
```
