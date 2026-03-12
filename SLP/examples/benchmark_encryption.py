#!/usr/bin/env python3
"""
Encryption Performance Benchmark

Benchmarks SLP encryption performance with different payload sizes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from slp.encryption.triple_layer import EncryptionMetrics


def main():
    """Run comprehensive encryption benchmarks."""
    print("="*70)
    print("🚀 SLP ENCRYPTION PERFORMANCE BENCHMARK")
    print("="*70)
    print()
    
    test_sizes = [
        (100, "100 bytes (small)"),
        (1024, "1 KB (typical)"),
        (10240, "10 KB (medium)"),
        (102400, "100 KB (large)"),
        (1048576, "1 MB (very large)")
    ]
    
    results = []
    
    for size, label in test_sizes:
        print(f"Testing {label}...")
        metrics = EncryptionMetrics.benchmark(size, iterations=50 if size < 100000 else 10)
        results.append((label, metrics))
        print(f"  Encrypt: {metrics['avg_encrypt_time_ms']:.3f} ms")
        print(f"  Decrypt: {metrics['avg_decrypt_time_ms']:.3f} ms")
        print(f"  Throughput: {metrics['encrypt_throughput_mbps']:.2f} MB/s\n")
    
    # Summary table
    print("="*70)
    print("PERFORMANCE SUMMARY")
    print("="*70)
    print(f"{'Payload Size':<20} {'Encrypt (ms)':<15} {'Decrypt (ms)':<15} {'Throughput (MB/s)':<20}")
    print("-"*70)
    
    for label, metrics in results:
        print(f"{label:<20} {metrics['avg_encrypt_time_ms']:<15.3f} {metrics['avg_decrypt_time_ms']:<15.3f} {metrics['encrypt_throughput_mbps']:<20.2f}")
    
    print("="*70)
    print("\n✅ Benchmark complete!")
    print("\nSecurity Layers:")
    print("  ✅ AES-256-GCM (Layer 1)")
    print("  ✅ ChaCha20-Poly1305 (Layer 2)")
    print("  ✅ Noise Protocol (Layer 3)")
    print("="*70)


if __name__ == "__main__":
    main()
