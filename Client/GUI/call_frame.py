import wx
import cv2
import numpy as np
import time

class CallFrame(wx.Frame):

    def __init__(self, call_logic):
        super().__init__(None, title="Meeting", size=(1024, 768))
        self.call_logic = call_logic

        # Start the call logic in background
        import threading
        threading.Thread(target=self.call_logic.start, daemon=True).start()

        panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # -----------------
        # Video grid
        # -----------------

        self.video_grid = wx.GridSizer(2, 2, 5, 5)
        self.video_panels = []

        camera_width, camera_height = 478, 359  # Frame size for 4:3 aspect ratio

        for i in range(4):
            bitmap = wx.StaticBitmap(panel)
            bitmap.SetMinSize((camera_width, camera_height))
            self.video_panels.append(bitmap)
            self.video_grid.Add(bitmap, 1, wx.EXPAND)

        main_sizer.Add(self.video_grid, 1, wx.EXPAND | wx.ALL, 10)

        # -----------------
        # Control bar
        # -----------------

        controls = wx.BoxSizer(wx.HORIZONTAL)

        self.mic_btn = wx.Button(panel, label="Mute")
        self.cam_btn = wx.Button(panel, label="Camera Off")
        self.leave_btn = wx.Button(panel, label="Leave")

        controls.Add(self.mic_btn, 0, wx.ALL, 5)
        controls.Add(self.cam_btn, 0, wx.ALL, 5)
        controls.AddStretchSpacer()
        controls.Add(self.leave_btn, 0, wx.ALL, 5)

        main_sizer.Add(controls, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)

        # Events
        self.leave_btn.Bind(wx.EVT_BUTTON, self.leave_call)
        self.mic_btn.Bind(wx.EVT_BUTTON, self.toggle_mic)
        self.cam_btn.Bind(wx.EVT_BUTTON, self.toggle_camera)

        # Track mute/camera state
        self.is_muted = False
        self.is_camera_off = False

        # Store frames for display
        self.client_frames = {}

        # fps
        self.last_update = 0
        self.fps = 24
        # Timer updates video
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_frames)
        self.timer.Start(int(1000/24))

    def update_frames(self, event):
        # Display own camera frame
        now = time.time()
        if now - self.last_update < 1 / self.fps:
            return  # skip this tick if too soon
        self.last_update = now
        if hasattr(self.call_logic, 'camera') and self.call_logic.camera:
            frame_bytes = self.call_logic.camera.get_frame()
            if frame_bytes is not None:
                # Decode JPEG bytes into a NumPy array
                frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    self._display_frame(0, frame)

        # Display frames from other participants
        if hasattr(self.call_logic, 'sync_buffer'):
            panel_idx = 1
            for client_ip, timestamps in list(self.call_logic.sync_buffer.items()):
                if panel_idx >= 4:
                    break
                for timestamp in sorted(timestamps.keys(), reverse=True):
                    data = timestamps[timestamp]
                    if data.get("video") is not None:
                        other_frame = data["video"]
                        self._display_frame(panel_idx, other_frame)
                        panel_idx += 1
                        break

    def _display_frame(self, panel_idx, frame):
        """Helper to display a frame in a specific video panel"""
        if frame is None or panel_idx >= len(self.video_panels):
            return

        try:
            # Resize frame to fit 478x359 display panel
            frame_resized = cv2.resize(frame, (478, 359))
            rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            bitmap = wx.Bitmap.FromBuffer(w, h, rgb)
            self.video_panels[panel_idx].SetBitmap(bitmap)
        except Exception as e:
            print("Display error:", e)

    def toggle_mic(self, event):
        """Toggle microphone mute/unmute"""
        if hasattr(self.call_logic, 'mic'):
            if self.is_muted:
                self.call_logic.mic.unmute()
                self.mic_btn.SetLabel("Mute")
                self.is_muted = False
            else:
                self.call_logic.mic.mute()
                self.mic_btn.SetLabel("Unmute")
                self.is_muted = True

    def toggle_camera(self, event):
        """Toggle camera on/off"""
        if hasattr(self.call_logic, 'camera'):
            if self.is_camera_off:
                self.call_logic.camera.start()
                self.cam_btn.SetLabel("Camera Off")
                self.is_camera_off = False
            else:
                self.call_logic.camera.stop()
                self.cam_btn.SetLabel("Camera On")
                self.is_camera_off = True

    def leave_call(self, event):
        """Leave the call and cleanup"""
        self.timer.Stop()

        # Stop devices
        if hasattr(self.call_logic, 'camera'):
            self.call_logic.camera.stop()
        if hasattr(self.call_logic, 'mic'):
            self.call_logic.mic.stop()
            self.call_logic.mic.close()

        self.Close()