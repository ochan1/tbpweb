# tbpweb
TBP CA-A website rework, build in Django

## Setup 

**Vagrant** will automatically setup a virtual machine with the correct
setup for developing `tbpweb`.

Install [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/wiki/Download_Old_Builds_6_0)
Try to install Virtual Box 6.0.14, as there have been some issues in the past with other versions of Virtual Box in terms of compatibility of Vagrant.

Fork the tbpweb repository and clone your fork to your local machine (you can clone using the Git from Mac Termainal, Windows Command Prompt, or Windows Git Bash (you may need to install Git to your Windows machine))

On Mac: Open **Terminal**

On Windows: Open **Command Prompt** as **Administrator** (not Git Bash)

Then, cd into the cloned directory.

Check to make sure there is a Vagrantfile in the directory. From there, type

```sh
$ vagrant up
```
(Note: If on Windows you encounter an Error 71, please make sure you 1) Are using Windows **Command Prompt** (not Git Bash), and 2) Run Windows Command Prompt as **Administrator**)

which will download and boot a Linux virtual machine, then setup the virtual machine.

To access the environment, run

```sh
$ vagrant ssh
```

which will `ssh` your terminal into the virtual machine.

See [Development](#development) for how to run the Django web server.

From here, run

```sh
$ cd tbpweb
```

Developing on `tbpweb` requires a virtual environment so that every developer has the exact same development environment i.e. any errors that a developer has is not due to difference in configuration. We will be using Python's built-on [`venv`](https://docs.python.org/3/library/venv.html) to make our virtual environment. This command creates our virtual environment.

```sh
$ make venv
```

(Note: If on Windows you encounter an Error 71, please make sure you 1) Are using Windows **Command Prompt** (not Git Bash), and 2) Run Windows Command Prompt as **Administrator**)

Next, we need to have our current terminal/shell use the virtual environment we just created. We do this through:

```sh
$ source .venv/bin/activate
```

To install all dependencies (including django), run

```sh
$ make install
```
There may be warnings that installation of some packages failed, but as long as you can run the command below successfully you are good to go.

If you make any Django changes (to the database models, for instance) you will have to create and migrate migrations. You can do so with the command below. If there were changes to database models made by other developers and you pulled those changes, you just have to run make migrate.
```sh
$ make migrations
$ make migrate
```

If you would like to access the admin interface, create a superuser using the command
```sh
$ make superuser
```

Finally, to run the web instance, simply run the command

```sh
$ make run
```
This will start the development server at http://0.0.0.0:3000/. If you go into your web browser and access localhost:3000, you should be able to see the site now!

To access the admin site, access http://0.0.0.0:3000/admin. Use the credentials you created for your superuser to login.

To exit out of the pipenv shell, run 

```sh
$ exit
```
The same command can be used to exit out of the virtual machine ssh connection.

To turn off the virtual machine, run

```sh
$ vagrant halt
```

which will attempt to safely shutdown the virtual machine, or kill it otherwise.


