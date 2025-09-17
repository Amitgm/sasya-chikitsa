# sasya-chikitsa
An AI driven application to help farmers and plant enthusiasts identify plant diseases and get useful recommendations.


## Instructions and Pre-requisites for Building the App
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


Step 2 : Update AndroidManifest.xml file with my code in app/src/main folder

Step 3 : Update activity_main.xml file with my code in app/src/main/res folder( This file should be in res/layout. If u don't find layout directory then create the Android Resource Directory and Rename it to layout and then create Android Resource File and rename it to activity_main.xml) 

Step 4 : Update MainActivity.kt file with my code in app/src/main/java folder

Step 5: Run on Emulator (Click Run Button on Top ) -- It will take 5-6 min to connect and Run the Emulator


## How to check logs

```bash
# get the temp token from the system admin or self generate.
oc login --token=$(echo $OCP_TOKEN) --server=https://api.cluster-mx6z7.mx6z7.sandbox5315.opentlc.com:6443

oc get pods -n sasya-chikitsa

oc logs -f engine-5947d8d5f5-w52l4 -n sasya-chikitsa 

oc logs -f llama318b-6984764f89-22vjl -n sasya-chikitsa
```

## Instruction for running MADR on local

```bash
❯ cd docs
❯ chruby ruby-3.4.1
❯ ruby -v
ruby 3.4.1 (2024-12-25 revision 48d4efcb85) +PRISM [arm64-darwin24]

❯ gem install bundler jekyll
Successfully installed bundler-2.7.1
Successfully installed jekyll-4.4.1
2 gems installed

❯ bundle install
Bundle complete! 6 Gemfile dependencies, 39 gems now installed.
Use `bundle info [gemname]` to see where a bundled gem is installed.

❯ bundle exec jekyll serve
Run in verbose mode to see all warnings.
                    done in 0.223 seconds.
 Auto-regeneration: enabled for '/Users/rajranja/Documents/github/cds-9-group-6/sasya-chikitsa/docs'
    Server address: http://127.0.0.1:4000/
  Server running... press ctrl-c to stop.

```