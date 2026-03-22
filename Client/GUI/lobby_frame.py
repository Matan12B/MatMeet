import wx
from call_frame import CallFrame


class LobbyFrame(wx.Frame):

    def __init__(self, host=False):
        super().__init__(None, title="Meeting Lobby", size=(400,300))

        self.host = host

        panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.code_text = wx.StaticText(panel, label="Meeting Code: 123456")

        self.participants = wx.ListBox(panel)

        vbox.Add(self.code_text, 0, wx.ALL | wx.CENTER, 10)
        vbox.Add(self.participants, 1, wx.ALL | wx.EXPAND, 10)

        if host:
            self.start_btn = wx.Button(panel, label="Start Call")
            vbox.Add(self.start_btn, 0, wx.ALL | wx.CENTER, 10)
            self.start_btn.Bind(wx.EVT_BUTTON, self.start_call)

        panel.SetSizer(vbox)

        # Fake users for testing
        self.participants.Append("Alice")
        self.participants.Append("Bob")


    def start_call(self, event):
        call = CallFrame()
        call.Show()
        self.Close()