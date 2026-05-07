import 'voice_service.dart';
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() => runApp(MouseControllerApp());

class MouseControllerApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Touch & Voice Control',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Color(0xFF1E1E2C),
        appBarTheme: AppBarTheme(backgroundColor: Color(0xFF2D2D44)),
      ),
      home: MouseControlScreen(),
    );
  }
}

class MouseControlScreen extends StatefulWidget {
  @override
  _MouseControlScreenState createState() => _MouseControlScreenState();
}

class _MouseControlScreenState extends State<MouseControlScreen> {
  final VoiceService _voiceService = VoiceService();
  String _voiceDebugText = "Scroll / Voice";

  RawDatagramSocket? _udpSocket;
  Offset? _lastPosition;

  String? _currentIP;
  bool _discovered = false;
  bool _manualOverride = false;
  List<String> _recentIPs = [];

  double _currentScale = 1.7;

  // --- משתנה חדש לשליטה במצלמה ---
  bool _isCameraEnabled = false;

  static const int COMMAND_PORT = 5000;
  static const int DISCOVERY_PORT = 5001;
  static const String DISCOVER_MSG = 'DISCOVER';
  static const String SERVER_RESP = 'MOUSE_SERVER';

  final List<Map<String, dynamic>> _quickActions = [
    {'label': 'Select', 'cmd': 'TOGGLE_SELECTION', 'icon': Icons.select_all},
    {'label': 'Copy', 'cmd': 'HOTKEY_CTRL_C', 'icon': Icons.copy},
    {'label': 'Paste', 'cmd': 'HOTKEY_CTRL_V', 'icon': Icons.paste},
    {'label': 'Cut', 'cmd': 'HOTKEY_CTRL_X', 'icon': Icons.content_cut},
    {'label': 'Undo', 'cmd': 'HOTKEY_CTRL_Z', 'icon': Icons.undo},
    {'label': 'Save', 'cmd': 'HOTKEY_CTRL_S', 'icon': Icons.save},
    {'label': 'Find', 'cmd': 'HOTKEY_CTRL_F', 'icon': Icons.search},
    {'label': 'Enter', 'cmd': 'HOTKEY_ENTER', 'icon': Icons.keyboard_return},
    {'label': 'F5', 'cmd': 'HOTKEY_F5', 'icon': Icons.refresh},
  ];

  @override
  void initState() {
    super.initState();
    _voiceService.initialize();
    _connectUdp();
  }

  void _connectUdp() {
    RawDatagramSocket.bind(InternetAddress.anyIPv4, 0).then((socket) {
      socket.broadcastEnabled = true;
      setState(() => _udpSocket = socket);
      _startListening();
      _discoverServer();
    });
  }

  void _startListening() {
    _udpSocket!.listen((event) {
      if (event == RawSocketEvent.read) {
        final dg = _udpSocket!.receive();
        if (dg != null) {
          final msg = utf8.decode(dg.data).trim();
          if (msg == SERVER_RESP && !_discovered && !_manualOverride) {
            setState(() {
              _currentIP = dg.address.address;
              _discovered = true;
            });
          }
        }
      }
    });
  }

  void _discoverServer() {
    if (_udpSocket == null || _discovered || _manualOverride) return;
    final data = utf8.encode(DISCOVER_MSG);
    _udpSocket!.send(data, InternetAddress('255.255.255.255'), DISCOVERY_PORT);
    Future.delayed(Duration(seconds: 2), () {
      if (!_discovered && !_manualOverride) _discoverServer();
    });
  }

  void _onRescan() {
    setState(() {
      _discovered = false;
      _manualOverride = false;
      _currentIP = null;
    });
    _discoverServer();
  }

  void _openSettings() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => SettingsScreen(
          initialIP: _currentIP ?? '',
          recentIPs: _recentIPs,
          currentScale: _currentScale,
        ),
      ),
    );

    if (result != null && result is Map) {
      if (result['ip'] != null && result['ip'].toString().isNotEmpty) {
        setState(() {
          _manualOverride = true;
          _discovered = true;
          _currentIP = result['ip'];
          if (!_recentIPs.contains(_currentIP)) {
            _recentIPs.insert(0, _currentIP!);
          }
        });
      }
      if (result['scale'] != null) {
        setState(() => _currentScale = result['scale']);
        _sendCommand('SET_SCALE:$_currentScale');
      }
    }
  }

  void _sendCommand(String cmd) {
    if (_udpSocket != null && _currentIP != null) {
      final data = utf8.encode(cmd + '\n');
      _udpSocket!.send(data, InternetAddress(_currentIP!), COMMAND_PORT);
      print('[UDP ➤ $_currentIP] $cmd');

      if (cmd.contains("CLICK") ||
          cmd.contains("ENTER") ||
          cmd.contains("HOTKEY")) {
        HapticFeedback.mediumImpact();
      } else if (!cmd.contains("MOVE") && !cmd.contains("SCALE")) {
        HapticFeedback.lightImpact();
      }
    }
  }

  // --- פונקציה חדשה להדלקה/כיבוי המצלמה ---
  void _toggleCamera() {
    setState(() {
      _isCameraEnabled = !_isCameraEnabled;
    });
    _sendCommand(_isCameraEnabled ? 'START_CAMERA' : 'STOP_CAMERA');
    HapticFeedback.heavyImpact();
  }

  void _processVoiceCommand(String text) {
    print("Voice received: $text");
    setState(() {
      if (text.isEmpty) {
        _voiceDebugText = "Listening...";
      } else {
        _voiceDebugText = text.toUpperCase();
      }
    });

    if (text.isNotEmpty) {
      _sendCommand('VOICE_RAW:$text');
      Future.delayed(Duration(seconds: 2), () {
        if (mounted && _voiceDebugText == text.toUpperCase()) {
          setState(() => _voiceDebugText = "Scroll / Voice");
        }
      });
    }
  }

  void _handlePanUpdate(DragUpdateDetails d) {
    final p = d.localPosition;
    if (_lastPosition != null) {
      final dx = p.dx - _lastPosition!.dx;
      final dy = p.dy - _lastPosition!.dy;
      if (dx != 0 || dy != 0) {
        _sendCommand('MOVE_DELTA:$dx,$dy');
      }
    }
    _lastPosition = p;
  }

  void _handlePanEnd(DragEndDetails _) => _lastPosition = null;

  void _handleScrollUpdate(DragUpdateDetails d) {
    // הגדלנו את המקדם מ-2.5 ל-5.0 כדי שהגלילה תהיה רגישה יותר
    double velocity = d.delta.dy * 5.0;

    if (velocity.abs() > 0.05) {
      // הורדנו את הסף כדי שכל תנועה תשלח פקודה
      _sendCommand('SCROLL_RAW:$velocity');
    }
  }

  void _leftClick() => _sendCommand('LEFT_CLICK');
  void _rightClick() => _sendCommand('RIGHT_CLICK');

  @override
  Widget build(BuildContext context) {
    final bool isConnected = _currentIP != null;
    final Color statusColor =
        isConnected ? Colors.greenAccent : Colors.redAccent;

    return Scaffold(
      appBar: AppBar(
        title: Text('Touch & Voice'),
        actions: [
          IconButton(icon: Icon(Icons.refresh), onPressed: _onRescan),
          IconButton(icon: Icon(Icons.settings), onPressed: _openSettings),
        ],
      ),
      body: Column(
        children: [
          Container(
            color: statusColor.withOpacity(0.1),
            padding: EdgeInsets.symmetric(vertical: 4),
            width: double.infinity,
            child: Center(
              child: Text(
                isConnected
                    ? 'Connected to $_currentIP'
                    : 'Disconnected (Check Settings)',
                style: TextStyle(color: statusColor, fontSize: 12),
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: Row(
                children: [
                  Expanded(
                    flex: 5,
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: _leftClick,
                      onDoubleTap: _rightClick,
                      onPanStart: (details) =>
                          _lastPosition = details.localPosition,
                      onPanUpdate: _handlePanUpdate,
                      onPanEnd: _handlePanEnd,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [Color(0xFF3A3A5E), Color(0xFF2B2B40)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: Center(
                            child: Icon(Icons.touch_app,
                                size: 48, color: Colors.white12)),
                      ),
                    ),
                  ),
                  SizedBox(width: 12),
                  Container(
                    width: 100,
                    child: Column(
                      children: [
                        // אזור הגלילה (Scroll)
                        Expanded(
                          flex: 3,
                          child: GestureDetector(
                            behavior: HitTestBehavior.opaque,
                            onVerticalDragUpdate: _handleScrollUpdate,
                            child: Container(
                              decoration: BoxDecoration(
                                color: Color(0xFF4A4A6A),
                                borderRadius: BorderRadius.vertical(
                                    top: Radius.circular(16)),
                                border: Border.all(color: Colors.white24),
                              ),
                              child: Center(
                                  child: Icon(Icons.unfold_more,
                                      color: Colors.white38)),
                            ),
                          ),
                        ),
                        SizedBox(height: 8),

                        // --- כפתור שליטה במצלמה (START/STOP) ---
                        Expanded(
                          flex: 1,
                          child: GestureDetector(
                            onTap: _toggleCamera,
                            child: Container(
                              width: double.infinity,
                              decoration: BoxDecoration(
                                color: _isCameraEnabled
                                    ? Colors.greenAccent.withOpacity(0.4)
                                    : Color(0xFF383850),
                                border: Border.all(
                                    color: _isCameraEnabled
                                        ? Colors.greenAccent
                                        : Colors.white24),
                              ),
                              child: Icon(
                                _isCameraEnabled
                                    ? Icons.videocam
                                    : Icons.videocam_off,
                                color: _isCameraEnabled
                                    ? Colors.greenAccent
                                    : Colors.white54,
                              ),
                            ),
                          ),
                        ),
                        SizedBox(height: 8),

                        // אזור המיקרופון (Voice)
                        Expanded(
                          flex: 1,
                          child: GestureDetector(
                            behavior: HitTestBehavior.opaque,
                            onLongPress: () {
                              _voiceService
                                  .listen((text) => _processVoiceCommand(text));
                              setState(() => _voiceDebugText = "Listening...");
                              HapticFeedback.heavyImpact();
                            },
                            onLongPressUp: () {
                              _voiceService.stop();
                              setState(
                                  () => _voiceDebugText = "Scroll / Voice");
                            },
                            child: Container(
                              decoration: BoxDecoration(
                                color: _voiceDebugText == "Listening..." ||
                                        _voiceDebugText != "Scroll / Voice"
                                    ? Colors.redAccent
                                    : Color(0xFF383850),
                                borderRadius: BorderRadius.vertical(
                                    bottom: Radius.circular(16)),
                                border: Border.all(color: Colors.white24),
                              ),
                              child: Center(
                                  child: _voiceDebugText == "Listening..." ||
                                          _voiceDebugText == "Scroll / Voice"
                                      ? Icon(
                                          _voiceDebugText == "Listening..."
                                              ? Icons.mic
                                              : Icons.mic_none,
                                          color: Colors.white)
                                      : Text(_voiceDebugText,
                                          style: TextStyle(
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                              color: Colors.white))),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(child: _buildButton('Left', Colors.blue, _leftClick)),
                SizedBox(width: 12),
                Expanded(
                    child: _buildButton('Right', Colors.purple, _rightClick)),
              ],
            ),
          ),
          SizedBox(height: 10),
          Container(
            height: 70,
            padding: EdgeInsets.only(bottom: 12),
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: EdgeInsets.symmetric(horizontal: 16),
              itemCount: _quickActions.length,
              itemBuilder: (context, index) {
                final action = _quickActions[index];
                return Padding(
                  padding: const EdgeInsets.only(right: 10),
                  child: ElevatedButton(
                    onPressed: () => _sendCommand(action['cmd']),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(action['icon'], size: 20),
                        Text(action['label'], style: TextStyle(fontSize: 10)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildButton(String label, Color color, VoidCallback onTap) {
    return Material(
      color: color.withOpacity(0.8),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: () {
          onTap();
          HapticFeedback.lightImpact();
        },
        child: Container(
            height: 60,
            alignment: Alignment.center,
            child: Text(label, style: TextStyle(fontWeight: FontWeight.bold))),
      ),
    );
  }
}

class SettingsScreen extends StatefulWidget {
  final String initialIP;
  final List<String> recentIPs;
  final double currentScale;

  SettingsScreen(
      {required this.initialIP,
      required this.recentIPs,
      required this.currentScale});

  @override
  _SettingsScreenState createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _ipController;
  late double _tempScale;

  @override
  void initState() {
    super.initState();
    _ipController = TextEditingController(text: widget.initialIP);
    _tempScale = widget.currentScale;
  }

  void _save() {
    Navigator.pop(
        context, {'ip': _ipController.text.trim(), 'scale': _tempScale});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Settings')),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(
                controller: _ipController,
                decoration: InputDecoration(labelText: 'Server IP')),
            Slider(
                value: _tempScale,
                min: 0.2,
                max: 5.0,
                onChanged: (v) => setState(() => _tempScale = v)),
            ElevatedButton(onPressed: _save, child: Text('Save')),
          ],
        ),
      ),
    );
  }
}
