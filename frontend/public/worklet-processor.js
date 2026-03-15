// worklet-processor.js
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = [];
    this.BLOCK_SIZE = 16000; // 1 second of audio at 16kHz
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channelData = input[0]; // mono input
    for (let i = 0; i < channelData.length; i++) {
      this.buffer.push(channelData[i]);
    }

    // Once 16000 samples are collected, send one full chunk
    if (this.buffer.length >= this.BLOCK_SIZE) {
      const block = this.buffer.splice(0, this.BLOCK_SIZE);
      const buffer = new ArrayBuffer(block.length * 2);
      const view = new DataView(buffer);

      // Convert Float32 [-1, 1] → Int16 PCM
      for (let i = 0; i < block.length; i++) {
        let s = Math.max(-1, Math.min(1, block[i]));
        view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      }

      this.port.postMessage(buffer);
    }

    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
