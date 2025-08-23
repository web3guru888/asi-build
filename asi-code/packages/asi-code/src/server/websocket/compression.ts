/**
 * WebSocket Compression and Binary Message Support
 *
 * Provides compression and binary message handling for WebSocket connections.
 * Includes deflate compression, binary message support, and efficient data transfer.
 */

import { createDeflate, createInflate } from 'zlib';
import { Transform } from 'stream';
import { nanoid } from 'nanoid';
import type {
  WSBinaryMessage,
  WSCompressionOptions,
  WSMessage,
} from './types.js';

export interface CompressionStats {
  messagesCompressed: number;
  messagesDecompressed: number;
  bytesBeforeCompression: number;
  bytesAfterCompression: number;
  compressionRatio: number;
  averageCompressionTime: number;
  averageDecompressionTime: number;
}

export class WSCompressionManager {
  private readonly config: WSCompressionOptions;
  private stats: CompressionStats = {
    messagesCompressed: 0,
    messagesDecompressed: 0,
    bytesBeforeCompression: 0,
    bytesAfterCompression: 0,
    compressionRatio: 0,
    averageCompressionTime: 0,
    averageDecompressionTime: 0,
  };

  constructor(config: WSCompressionOptions) {
    this.config = {
      enabled: true,
      threshold: 1024,
      level: 6,
      windowBits: 15,
      memLevel: 8,
      ...config,
    };
  }

  /**
   * Compress a message if it meets the threshold
   */
  async compressMessage(message: string | Buffer): Promise<{
    data: Buffer;
    compressed: boolean;
    originalSize: number;
    compressedSize: number;
  }> {
    if (!this.config.enabled) {
      const buffer = Buffer.isBuffer(message)
        ? message
        : Buffer.from(message, 'utf8');
      return {
        data: buffer,
        compressed: false,
        originalSize: buffer.length,
        compressedSize: buffer.length,
      };
    }

    const startTime = Date.now();
    const inputBuffer = Buffer.isBuffer(message)
      ? message
      : Buffer.from(message, 'utf8');
    const originalSize = inputBuffer.length;

    if (originalSize < this.config.threshold) {
      return {
        data: inputBuffer,
        compressed: false,
        originalSize,
        compressedSize: originalSize,
      };
    }

    try {
      const compressed = await this.deflateBuffer(inputBuffer);
      const compressedSize = compressed.length;
      const compressionTime = Date.now() - startTime;

      // Update stats
      this.stats.messagesCompressed++;
      this.stats.bytesBeforeCompression += originalSize;
      this.stats.bytesAfterCompression += compressedSize;
      this.updateAverageCompressionTime(compressionTime);
      this.updateCompressionRatio();

      return {
        data: compressed,
        compressed: true,
        originalSize,
        compressedSize,
      };
    } catch (error) {
      console.error('Compression error:', error);
      return {
        data: inputBuffer,
        compressed: false,
        originalSize,
        compressedSize: originalSize,
      };
    }
  }

  /**
   * Decompress a message
   */
  async decompressMessage(
    data: Buffer,
    wasCompressed: boolean
  ): Promise<{
    data: Buffer;
    originalSize: number;
    decompressedSize: number;
  }> {
    if (!wasCompressed) {
      return {
        data,
        originalSize: data.length,
        decompressedSize: data.length,
      };
    }

    const startTime = Date.now();
    const originalSize = data.length;

    try {
      const decompressed = await this.inflateBuffer(data);
      const decompressedSize = decompressed.length;
      const decompressionTime = Date.now() - startTime;

      // Update stats
      this.stats.messagesDecompressed++;
      this.updateAverageDecompressionTime(decompressionTime);

      return {
        data: decompressed,
        originalSize,
        decompressedSize,
      };
    } catch (error) {
      console.error('Decompression error:', error);
      throw new Error('Failed to decompress message');
    }
  }

  /**
   * Create a compressed WebSocket message
   */
  async createCompressedMessage(message: WSMessage): Promise<{
    data: Buffer;
    headers: Record<string, any>;
  }> {
    const messageStr = JSON.stringify(message);
    const result = await this.compressMessage(messageStr);

    const headers: Record<string, any> = {
      'x-original-size': result.originalSize,
      'x-compressed-size': result.compressedSize,
      'x-compressed': result.compressed,
    };

    if (result.compressed) {
      headers['content-encoding'] = 'deflate';
    }

    return {
      data: result.data,
      headers,
    };
  }

  /**
   * Parse a potentially compressed WebSocket message
   */
  async parseCompressedMessage(
    data: Buffer,
    headers?: Record<string, any>
  ): Promise<WSMessage> {
    const wasCompressed =
      headers?.['x-compressed'] === true ||
      headers?.['content-encoding'] === 'deflate';

    const result = await this.decompressMessage(data, wasCompressed);
    const messageStr = result.data.toString('utf8');

    return JSON.parse(messageStr);
  }

  /**
   * Get compression statistics
   */
  getStats(): CompressionStats {
    return { ...this.stats };
  }

  /**
   * Reset compression statistics
   */
  resetStats(): void {
    this.stats = {
      messagesCompressed: 0,
      messagesDecompressed: 0,
      bytesBeforeCompression: 0,
      bytesAfterCompression: 0,
      compressionRatio: 0,
      averageCompressionTime: 0,
      averageDecompressionTime: 0,
    };
  }

  /**
   * Deflate (compress) buffer
   */
  private deflateBuffer(input: Buffer): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      const deflateStream = createDeflate({
        level: this.config.level,
        windowBits: this.config.windowBits,
        memLevel: this.config.memLevel,
      });

      deflateStream.on('data', chunk => {
        chunks.push(chunk);
      });

      deflateStream.on('end', () => {
        resolve(Buffer.concat(chunks));
      });

      deflateStream.on('error', error => {
        reject(error);
      });

      deflateStream.write(input);
      deflateStream.end();
    });
  }

  /**
   * Inflate (decompress) buffer
   */
  private inflateBuffer(input: Buffer): Promise<Buffer> {
    return new Promise((resolve, reject) => {
      const chunks: Buffer[] = [];
      const inflateStream = createInflate({
        windowBits: this.config.windowBits,
      });

      inflateStream.on('data', chunk => {
        chunks.push(chunk);
      });

      inflateStream.on('end', () => {
        resolve(Buffer.concat(chunks));
      });

      inflateStream.on('error', error => {
        reject(error);
      });

      inflateStream.write(input);
      inflateStream.end();
    });
  }

  /**
   * Update average compression time
   */
  private updateAverageCompressionTime(time: number): void {
    const count = this.stats.messagesCompressed;
    this.stats.averageCompressionTime =
      (this.stats.averageCompressionTime * (count - 1) + time) / count;
  }

  /**
   * Update average decompression time
   */
  private updateAverageDecompressionTime(time: number): void {
    const count = this.stats.messagesDecompressed;
    this.stats.averageDecompressionTime =
      (this.stats.averageDecompressionTime * (count - 1) + time) / count;
  }

  /**
   * Update compression ratio
   */
  private updateCompressionRatio(): void {
    if (this.stats.bytesBeforeCompression > 0) {
      this.stats.compressionRatio =
        this.stats.bytesAfterCompression / this.stats.bytesBeforeCompression;
    }
  }
}

export class WSBinaryManager {
  private readonly config: {
    maxSize: number;
    allowedTypes: string[];
    checksumEnabled: boolean;
  };

  constructor(
    config: {
      maxSize?: number;
      allowedTypes?: string[];
      checksumEnabled?: boolean;
    } = {}
  ) {
    this.config = {
      maxSize: 10 * 1024 * 1024, // 10MB
      allowedTypes: [
        'application/octet-stream',
        'application/json',
        'text/plain',
      ],
      checksumEnabled: true,
      ...config,
    };
  }

  /**
   * Create binary message
   */
  createBinaryMessage(
    type: string,
    data: Buffer | ArrayBuffer | string,
    metadata?: Record<string, any>
  ): WSBinaryMessage {
    let buffer: Buffer;
    let format: 'buffer' | 'arraybuffer' | 'base64';

    if (Buffer.isBuffer(data)) {
      buffer = data;
      format = 'buffer';
    } else if (data instanceof ArrayBuffer) {
      buffer = Buffer.from(data);
      format = 'arraybuffer';
    } else {
      buffer = Buffer.from(data, 'utf8');
      format = 'base64';
    }

    if (buffer.length > this.config.maxSize) {
      throw new Error(
        `Binary message too large: ${buffer.length} > ${this.config.maxSize}`
      );
    }

    const checksum = this.config.checksumEnabled
      ? this.calculateChecksum(buffer)
      : undefined;

    return {
      id: nanoid(),
      type,
      format,
      data: this.encodeData(buffer, format),
      size: buffer.length,
      checksum,
      metadata,
    };
  }

  /**
   * Parse binary message
   */
  parseBinaryMessage(message: WSBinaryMessage): {
    type: string;
    data: Buffer;
    size: number;
    metadata?: Record<string, any>;
    valid: boolean;
  } {
    const buffer = this.decodeData(message.data, message.format);

    // Verify checksum if present
    let valid = true;
    if (message.checksum && this.config.checksumEnabled) {
      const calculatedChecksum = this.calculateChecksum(buffer);
      valid = calculatedChecksum === message.checksum;
    }

    // Verify size
    if (buffer.length !== message.size) {
      valid = false;
    }

    return {
      type: message.type,
      data: buffer,
      size: buffer.length,
      metadata: message.metadata,
      valid,
    };
  }

  /**
   * Validate binary message type
   */
  validateBinaryType(type: string): boolean {
    return (
      this.config.allowedTypes.length === 0 ||
      this.config.allowedTypes.includes(type)
    );
  }

  /**
   * Split large binary message into chunks
   */
  chunkBinaryMessage(
    message: WSBinaryMessage,
    chunkSize: number = 64 * 1024 // 64KB chunks
  ): WSBinaryMessage[] {
    const buffer = this.decodeData(message.data, message.format);

    if (buffer.length <= chunkSize) {
      return [message];
    }

    const chunks: WSBinaryMessage[] = [];
    const totalChunks = Math.ceil(buffer.length / chunkSize);

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, buffer.length);
      const chunkBuffer = buffer.slice(start, end);

      const chunkMessage: WSBinaryMessage = {
        id: `${message.id}_chunk_${i}`,
        type: message.type,
        format: 'buffer',
        data: chunkBuffer,
        size: chunkBuffer.length,
        checksum: this.config.checksumEnabled
          ? this.calculateChecksum(chunkBuffer)
          : undefined,
        metadata: {
          ...message.metadata,
          isChunk: true,
          chunkIndex: i,
          totalChunks,
          originalId: message.id,
          originalSize: message.size,
        },
      };

      chunks.push(chunkMessage);
    }

    return chunks;
  }

  /**
   * Reassemble chunked binary message
   */
  reassembleChunkedMessage(chunks: WSBinaryMessage[]): WSBinaryMessage | null {
    if (chunks.length === 0) return null;

    // Sort chunks by index
    chunks.sort((a, b) => {
      const indexA = a.metadata?.chunkIndex ?? 0;
      const indexB = b.metadata?.chunkIndex ?? 0;
      return indexA - indexB;
    });

    const firstChunk = chunks[0];
    const originalId = firstChunk.metadata?.originalId;
    const totalChunks = firstChunk.metadata?.totalChunks;
    const originalSize = firstChunk.metadata?.originalSize;

    if (!originalId || !totalChunks || chunks.length !== totalChunks) {
      return null;
    }

    // Reassemble data
    const buffers: Buffer[] = [];
    for (const chunk of chunks) {
      const chunkData = this.decodeData(chunk.data, chunk.format);
      buffers.push(chunkData);
    }

    const reassembledBuffer = Buffer.concat(buffers);

    // Verify size
    if (originalSize && reassembledBuffer.length !== originalSize) {
      return null;
    }

    return {
      id: originalId,
      type: firstChunk.type,
      format: 'buffer',
      data: reassembledBuffer,
      size: reassembledBuffer.length,
      checksum: this.config.checksumEnabled
        ? this.calculateChecksum(reassembledBuffer)
        : undefined,
      metadata: {
        ...firstChunk.metadata,
        isChunk: false,
        reassembled: true,
      },
    };
  }

  /**
   * Encode data based on format
   */
  private encodeData(
    buffer: Buffer,
    format: 'buffer' | 'arraybuffer' | 'base64'
  ): any {
    switch (format) {
      case 'buffer':
        return buffer;
      case 'arraybuffer':
        return buffer.buffer.slice(
          buffer.byteOffset,
          buffer.byteOffset + buffer.byteLength
        );
      case 'base64':
        return buffer.toString('base64');
      default:
        throw new Error(`Unsupported format: ${format}`);
    }
  }

  /**
   * Decode data based on format
   */
  private decodeData(
    data: any,
    format: 'buffer' | 'arraybuffer' | 'base64'
  ): Buffer {
    switch (format) {
      case 'buffer':
        return Buffer.isBuffer(data) ? data : Buffer.from(data);
      case 'arraybuffer':
        return Buffer.from(data);
      case 'base64':
        return Buffer.from(data, 'base64');
      default:
        throw new Error(`Unsupported format: ${format}`);
    }
  }

  /**
   * Calculate checksum (simple CRC32)
   */
  private calculateChecksum(buffer: Buffer): string {
    // Simple CRC32 implementation
    let crc = 0xffffffff;
    const table = this.getCRC32Table();

    for (let i = 0; i < buffer.length; i++) {
      crc = table[(crc ^ buffer[i]) & 0xff] ^ (crc >>> 8);
    }

    return ((crc ^ 0xffffffff) >>> 0).toString(16);
  }

  /**
   * Get CRC32 table
   */
  private getCRC32Table(): Uint32Array {
    const table = new Uint32Array(256);

    for (let i = 0; i < 256; i++) {
      let crc = i;
      for (let j = 0; j < 8; j++) {
        crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
      }
      table[i] = crc;
    }

    return table;
  }
}

/**
 * Utility functions for WebSocket compression and binary handling
 */
export class WSMessageUtils {
  /**
   * Determine if message should be compressed
   */
  static shouldCompress(message: WSMessage, threshold: number = 1024): boolean {
    const messageStr = JSON.stringify(message);
    return Buffer.byteLength(messageStr, 'utf8') >= threshold;
  }

  /**
   * Estimate compression savings
   */
  static estimateCompressionSavings(data: string | Buffer): number {
    const input = typeof data === 'string' ? data : data.toString();

    // Simple heuristic: count repeated patterns
    const uniqueChars = new Set(input).size;
    const totalChars = input.length;

    if (totalChars === 0) return 0;

    // Higher redundancy = better compression
    const redundancy = 1 - uniqueChars / totalChars;
    return Math.min(redundancy * 0.7, 0.8); // Max 80% compression
  }

  /**
   * Convert WebSocket message to binary format
   */
  static messageToBinary(message: WSMessage): Buffer {
    const messageStr = JSON.stringify(message);
    return Buffer.from(messageStr, 'utf8');
  }

  /**
   * Convert binary data to WebSocket message
   */
  static binaryToMessage(data: Buffer): WSMessage {
    const messageStr = data.toString('utf8');
    return JSON.parse(messageStr);
  }

  /**
   * Create streaming message chunks
   */
  static createStreamingChunks(
    data: string,
    chunkSize: number = 1024,
    messageType: string = 'stream:chunk'
  ): WSMessage[] {
    const chunks: WSMessage[] = [];
    const totalChunks = Math.ceil(data.length / chunkSize);
    const streamId = nanoid();

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, data.length);
      const chunk = data.slice(start, end);

      chunks.push({
        id: nanoid(),
        type: messageType,
        timestamp: Date.now(),
        data: {
          streamId,
          chunkIndex: i,
          totalChunks,
          chunk,
          isLast: i === totalChunks - 1,
        },
      });
    }

    return chunks;
  }

  /**
   * Reassemble streaming chunks
   */
  static reassembleStreamingChunks(chunks: WSMessage[]): string {
    // Sort by chunk index
    chunks.sort((a, b) => {
      const indexA = a.data?.chunkIndex ?? 0;
      const indexB = b.data?.chunkIndex ?? 0;
      return indexA - indexB;
    });

    // Concatenate chunks
    return chunks.map(chunk => chunk.data?.chunk ?? '').join('');
  }
}
