import 'package:speech_to_text/speech_to_text.dart' as stt;

class VoiceService {
  stt.SpeechToText _speech = stt.SpeechToText();
  bool _isAvailable = false;

  void initialize() async {
    print("🎤 VoiceService: Initializing...");
    try {
      _isAvailable = await _speech.initialize(
        onStatus: (status) => print('🎤 Status Update: $status'),
        onError: (errorNotification) =>
            print('❌ Voice Error: ${errorNotification.errorMsg}'),
      );
      print("🎤 Initialization Result: Available = $_isAvailable");
    } catch (e) {
      print("❌ CRITICAL ERROR in VoiceService: $e");
    }
  }

  void listen(Function(String) onResult) {
    if (!_isAvailable) {
      print("⚠️ VoiceService not available! Cannot listen.");
      initialize();
      return;
    }

    print("🎤 Starting to listen...");
    _speech.listen(
      onResult: (val) {
        print("🗣️ Heard raw words: ${val.recognizedWords}");
        onResult(val.recognizedWords);
      },
      localeId: 'he_IL',
      listenFor: Duration(seconds: 10),
      pauseFor: Duration(seconds: 3),
      partialResults: true,
      cancelOnError: true,
      listenMode: stt.ListenMode.dictation,
    );
  }

  void stop() {
    print("🛑 VoiceService: Stop called");
    _speech.stop();
  }
}
