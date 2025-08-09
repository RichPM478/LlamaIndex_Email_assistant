# check_gpu.py
import sys
import subprocess

print("=" * 60)
print("GPU DIAGNOSTICS FOR LLAMAINDEX EMAIL ASSISTANT")
print("=" * 60)

# 1. Check PyTorch GPU support
try:
    import torch
    print("\n✅ PyTorch installed")
    print(f"   Version: {torch.__version__}")
    
    if torch.cuda.is_available():
        print(f"\n🚀 CUDA is available!")
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   GPU Count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"   GPU {i}: {torch.cuda.get_device_name(i)}")
            props = torch.cuda.get_device_properties(i)
            print(f"      Memory: {props.total_memory / 1024**3:.1f} GB")
            print(f"      Compute Capability: {props.major}.{props.minor}")
    else:
        print("\n⚠️ CUDA not available - using CPU")
        print("   To enable GPU acceleration:")
        print("   1. Ensure you have an NVIDIA GPU")
        print("   2. Install CUDA Toolkit 11.8 or 12.1")
        print("   3. Reinstall PyTorch with CUDA support:")
        print("      pip install torch --index-url https://download.pytorch.org/whl/cu118")
except ImportError:
    print("\n❌ PyTorch not installed")
    print("   Install with: pip install torch")

# 2. Check sentence-transformers GPU support
try:
    from sentence_transformers import SentenceTransformer
    import time
    
    print("\n" + "="*40)
    print("EMBEDDING PERFORMANCE TEST")
    print("="*40)
    
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    test_texts = ["This is a test email about a school event"] * 100
    
    # CPU test
    if torch.cuda.is_available():
        model = model.to('cpu')
    start = time.time()
    cpu_embeddings = model.encode(test_texts, show_progress_bar=False)
    cpu_time = time.time() - start
    print(f"\nCPU Performance:")
    print(f"   100 embeddings in {cpu_time:.2f}s")
    print(f"   Speed: {100/cpu_time:.0f} embeddings/sec")
    
    # GPU test (if available)
    if torch.cuda.is_available():
        model = model.to('cuda')
        
        # Warmup
        _ = model.encode(["warmup"], show_progress_bar=False)
        
        start = time.time()
        gpu_embeddings = model.encode(test_texts, show_progress_bar=False)
        gpu_time = time.time() - start
        print(f"\nGPU Performance:")
        print(f"   100 embeddings in {gpu_time:.2f}s")
        print(f"   Speed: {100/gpu_time:.0f} embeddings/sec")
        print(f"\n🎯 Speedup: {cpu_time/gpu_time:.1f}x faster on GPU!")
        
except ImportError:
    print("\n❌ sentence-transformers not installed")

# 3. Check Ollama GPU support
print("\n" + "="*40)
print("OLLAMA GPU CHECK")
print("="*40)

try:
    result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Ollama is installed")
        if 'GPU' in result.stdout or 'gpu' in result.stdout.lower():
            print("🚀 Ollama appears to be using GPU")
        else:
            print("⚠️ Ollama may be using CPU only")
        print("\nOllama status:")
        print(result.stdout)
    else:
        print("⚠️ Ollama not running")
except FileNotFoundError:
    print("❌ Ollama not found in PATH")
    print("   Install from: https://ollama.ai")

# 4. Recommendations
print("\n" + "="*60)
print("RECOMMENDATIONS FOR YOUR SYSTEM")
print("="*60)

if torch.cuda.is_available():
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    
    if vram >= 8:
        print("✅ You have enough VRAM for:")
        print("   - Large embedding models (bge-large)")
        print("   - 7B parameter LLMs (Mistral, Llama 3)")
        print("   - Fast batch processing")
    elif vram >= 4:
        print("✅ You have enough VRAM for:")
        print("   - Medium embedding models (mpnet-base)")
        print("   - 3B parameter LLMs (Llama 3.2:3b)")
        print("   - Moderate batch processing")
    else:
        print("⚠️ Limited VRAM. Recommended:")
        print("   - Small embedding models (MiniLM)")
        print("   - Quantized LLMs (Q4 versions)")
        print("   - Smaller batch sizes")
    
    print("\n🚀 To maximize GPU usage:")
    print("   1. Set in .env: EMBEDDING_BATCH_SIZE=32")
    print("   2. Use quantized Ollama models: llama3.2:3b-instruct-q4_K_M")
    print("   3. Consider using GGUF models for better memory efficiency")
else:
    print("💡 To enable GPU acceleration:")
    print("   1. Check if you have an NVIDIA GPU: nvidia-smi")
    print("   2. Install CUDA Toolkit from NVIDIA")
    print("   3. Reinstall PyTorch with CUDA:")
    print("      pip uninstall torch torchvision torchaudio")
    print("      pip install torch --index-url https://download.pytorch.org/whl/cu118")

print("\n" + "="*60)