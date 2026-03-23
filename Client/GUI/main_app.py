import wx
from home_frame import HomeFrame
from MatMeet.Client.Logic.clientLogic import Client

class ZoomApp(wx.App):

    def OnInit(self):
        # Pass None for client to run in UI-only mode
        self.client = Client("192.168.4.74", 3018)
        frame = HomeFrame(client=self.client)
        frame.Show()
        return True

if __name__ == "__main__":
    app = ZoomApp()
    app.MainLoop()