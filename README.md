# python-services
# Setting env 
1. sudo apt-get install python3-venv
2. linux => python3 -m venv .
## windows
3. pip install virtualenv
4. windows => python -m virtualenv .
5. abra o powershell como adm 
6. Set-ExecutionPolicy -ExecutionPolicy RemoteSigned


## activating and deactivating virtual env
### linux
1. . bin/activate
2. deactivate
### windows (not sure if it works properly)
1. .\Scripts\activate
2. .\Scripts\deactivate

## install dependencies with pip
python3 -m pip install -r requirements.txt