I usually work on very different type of assets such as Digital assets in Houdini, meshes, textures etc.
I wanted to have a easy versioning control over these objects just like my python code on github. That is why I decided to create my own tool for that directly embedded in 3D apps using Python.

I decided to go with Amazon Web Service S3 simple storage, it allows you to keep former version of your assets and have a decent pricing model as well. It comes with a neat python API and it's also easily scalable.

This tool works on a base of "project", a project is just a folders hierachy where you save your assets and scenes. These folders also exist on the Amazon Cloud. You can then send and get data from / to the cloud direclty you app.
As it is fully python code only ( with PySide2 for UI and boto3 amazon API ), it can be used in many 3D packages which support python ( Maya, Nuke, Houdini, ... ) or even as a standalone app. The video of example bellow is made in Houdini only because it's my main 3D package.

It also support a lock system where you can "lock" a file you want to work on. The file is then locked on the cloud. If another artist want to work on that asset he / she will have to wait until you finished your task  on that asset ( until you submit your asset on the cloud or unlock your file ). This process ( very well known as "checkout asset" in Perforce system for instance ) allows you to safely work with multiple artists on the same project without overlapping your work.

It also comes with a "plugin" system which allows you to execute python scrits after an action such as, Get a file, Lock a file, Save a file or Click on icon. This, according a filters ( type of files, software etc.).
This allows you for instance to reload a geometry after getting a new version, reloading an digital asset etc.

This tool is designed to work with Amazon S3 system but the in / out interface is one python file, which can be changed to use another cloud provider as long as they have python API available.

More infos: http://guillaumejobst.blogspot.fr/2017/06/versioning-control-over-cloud-embedded.html
