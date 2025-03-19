# rflink_somfy
Command line client to interact with RFLink for Somfy blinds

## Usage
```
$ python rflink_somfy.py
Somfy RFLink Client
===================

Connected to device: Nodo RadioFrequencyLink, RFLink Gateway V1.1 rev. 48
writing data: 10;RTSSHOW;

Channel  Address    Rolling Code    Active
-------  -------  ----------------  ------
   0     AAAAAA        2 [0x0002]    True
   1     BBBBBB     1772 [0x06EC]    True
   2     CCCCCC      330 [0x014A]    True
   3     DDDDDD      491 [0x01EB]    True
   4     EEEEEE     4141 [0x102D]    True
   5     999999     2281 [0x08E9]    True
   6     FFFFFF                      False
   7     FFFFFF                      False
   8     FFFFFF                      False
   9     FFFFFF                      False
  10     FFFFFF                      False
  11     FFFFFF                      False
  12     FFFFFF                      False
  13     FFFFFF                      False
  14     FFFFFF                      False
  15     FFFFFF                      False
Please enter the channel you wish to interact with: 
Channel: 

``` 

You need to have the serial port available, so if you are running this on the same machine as a home automation that is using the RFLink you'll need to stop that first.

Port was /dev/ttyACM0 on Linux and /dev/cu.usbmodem1001 on MacOS. Port can be set by passing it to command line.

```
$ python rflink_somfy.py /dev/cu.usbmodem1001

Somfy RFLink Client
===================
```

## Why?

I needed to pair some new blinds with our RFLink so the home automation could control them. It's bare bones and overly simple, but it did what I needed :-)

Maybe someone else will find it useful.
