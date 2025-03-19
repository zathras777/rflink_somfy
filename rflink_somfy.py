import sys
import asyncio
import random
from serial_asyncio import create_serial_connection
from typing import Optional

class RTSChannel:
    def __init__(self, parts: str):
        records = parts.split(" ")
        if len(records) < 7:
            print(f"Invalid data to convert to Channel Record: {parts}")
            return
        self.id = int(records[2])
        self.address = records[4]
        self.rolling = int(records[6], 16)

    def __str__(self) -> str:
        if self.address == "FFFFFF":
            return f"Record {self.id:2d}: Address: {self.address}  Rolling Code: n/a"
        return f"Record {self.id:2d}: Address: {self.address}  Rolling Code: {self.rolling:5d} [{self.rolling:04x}]"

    @property
    def isActive(self) -> bool:
        return self.address != "FFFFFF"

    def createCommand(self, command:str) -> str:
        parts = ["10", "RTS", self.address, f"{self.id:X}", command]
        if command == "PAIR":
            if self.rolling == 0xffff:
                self.rolling = 0x0001
            if self.address == "FFFFFF":
                self.address = ''.join(random.choices('0123456789ABCDEF', k=6))
                parts[2] = self.address
            parts.insert(3, f"{self.rolling:04X}")
        self.rolling += 1
        return ";".join(parts) + ";"


class SimpleRFLink(asyncio.Protocol):
    transport = None  # type: asyncio.BaseTransport
    keepalive = None  # type: Optional[int]

    def __init__(self, loop = None):
        self.loop = loop
        if loop is None:
            self.loop = asyncio.get_event_loop()
        self.connection = None
        self.channels = {}
        self.futures = []
        self.buffer = ""
        self.open_future = asyncio.Future()
        self.channelFuture = None

    async def waitForConnection(self) -> bool:
        try:
            await asyncio.wait_for(self.open_future, 5.0)
            return self.open_future.result()
        except TimeoutError:
            print("Timed out waiting for welcome message to be received,")
            return False

    async def getRTSInformation(self) -> bool:
        self.channels = {}
        self.channelFuture = asyncio.Future()
        self._write("10;RTSSHOW;")
        await asyncio.wait_for(self.channelFuture, 5.0)
        if self.channelFuture.done():
            return len(self.channels) == 16
        print("Channel future never triggered?")
        return False

    def showRTSChannels(self):
        print("\nChannel  Address    Rolling Code    Active")
        print(  "-------  -------  ----------------  ------")
        for n in sorted(self.channels.keys()):
            chan = self.channels[n]
            print(f"  {n:2d}     {chan.address}    ", end="")
            #{chan.rolling:>5d} [0x{chan.rolling:04X}]    {chan.isActive}")

            if chan.rolling == 0xffff:
                print("              ", end="")
            else:
                print(f"{chan.rolling:>5d} [0x{chan.rolling:04X}]", end = "")
            print(f"    {chan.isActive}")
 
    async def doCommand(self, channelNo: int, cmdString: str):
        chan = self._getChannel(channelNo, cmdString != "PAIR")
        if chan == None:
            return
        resp = await self._do_command(chan.createCommand(cmdString))
        print(f"    Result: {resp}")

    ## Serial Connection handling
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Just logging for now."""
        self.transport = transport

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Log when connection is closed, if needed call callback."""
        if exc:
            print(exc)
        self.transport = None
        for f in self.futures:
            f.set_result(False)

    def data_received(self, data: bytes) -> None:
        """Add incoming data to buffer."""
        try:
            decoded_data = data.decode()
        except UnicodeDecodeError:
            invalid_data = data.decode(errors="replace")
            print(f"Error during decode of data, invalid data: {invalid_data}")
        else:
            self.buffer += decoded_data
            added = 0
            while "\r\n" in self.buffer:
                line, self.buffer = self.buffer.split("\r\n", 1)
                self._process_message(line)

    ## Internal functions...
    def _getChannel(self, channelNo:int, mustBeActive: bool) -> RTSChannel:                                                         
        if not channelNo in self.channels.keys():                                     
            print(f"Invalid channel number {channelNo}.")                          
            return None                     
        channel = self.channels[channelNo]
        if not channel.isActive and mustBeActive:
            print(f"Channel {channelNo} is not active. Do you need to pair a blind?")
            return None
        return channel

    def _setDevice(self, deviceStr):                                         
        parts = deviceStr.split(" - ")
        product = parts[0].strip()
        name = parts[1].strip()
        revision = parts[2].strip().replace("R", "")
        print(f"Connected to device: {product}, {name} rev. {revision}")
        self.open_future.set_result(True)
    
    def _process_message(self, line: str):
        if line.startswith("RTS Record"):
            rts = RTSChannel(line)
            self.channels[rts.id] = rts
            if len(self.channels) == 16:
                self.channelFuture.set_result(True)

        elif line.startswith("20;"): 
            parts = line.strip().split(";")
            if parts[1] == "00":
                self._setDevice(parts[2])
            elif len(parts) == 4:
                future = self.futures.pop(0)
                future.set_result(parts[2]) 
            else:
                print(parts)
        else:
            print(line)

    async def _do_command(self, command: str):    
        future = asyncio.Future()
        self.futures.append(future)
        self._write(command)
        await asyncio.wait_for(future, 5.0)
        return future.result()
    
    def _write(self, command:str):
        print(f"writing data: {command}")
        self.transport.write(f"{command}\r\n".encode())
                                                                                                                                               

async def processCommands(rflink: SimpleRFLink, channelNo: int):
    print(f"\nEnter commands to send to the blind on channel {channelNo}.")

    while True:                                                              
        print("Valid commands are: UP, DOWN, STOP, MY, PAIR, QUIT. [ENTER to finish]. Case is not important.")
        cmd = input(f"Channel {channelNo} Command: ").strip().upper()                                                     
        if len(cmd) == 0 or cmd == "QUIT":
            print("Finished\n")                                                                    
            break                                                                

        if cmd not in ["UP", "DOWN", "STOP", "MY", "PAIR"]:
            print("Invalid command. Ignored")
            continue

        if cmd == "MY":
            cmd = "STOP"

        await rflink.doCommand(channelNo, cmd)
        print("")

async def main():
    print("Somfy RFLink Client\n===================\n")

    port = "/dev/ttyACM0"
    if len(sys.argv) > 1:
        port = sys.argv[1]

    loop = asyncio.get_event_loop()
    rflink = SimpleRFLink(loop = loop)
    conn, _ = await create_serial_connection(loop, lambda: rflink, port, 57600)

    if await rflink.waitForConnection():
        while True:
            if await rflink.getRTSInformation():
                rflink.showRTSChannels()

            print("Please enter the channel you wish to interact with: ")
            chan = input("Channel: ").strip()                                                       
            if len(chan) == 0:                                                                      
                break                                                                               
                                                                                                    
            if not chan.isdigit():                                                                  
                print("Non numeric answer ignored :-)\n")
            else:                                                                                   
                await processCommands(rflink, int(chan))

    conn.close()

if __name__ == '__main__':
    asyncio.run(main())
