"""
Setup script for the Flexible Email Intelligence System
Builds the initial index and prepares for experimentation
"""
import sys
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def setup_flexible_system():
    """Setup the flexible experimental system"""
    
    print("🚀 Setting up Flexible Email Intelligence System...")
    print("=" * 60)
    
    # Step 1: Check if we have raw emails
    raw_email_file = "data/raw/emails_20250822_225800.json"
    if not Path(raw_email_file).exists():
        print(f"❌ Raw email file not found: {raw_email_file}")
        print("Please run email ingestion first:")
        print("python main.py ingest")
        return False
    
    print(f"✅ Found raw emails: {raw_email_file}")
    
    # Step 2: Install required packages
    print("\n📦 Checking dependencies...")
    try:
        import sentence_transformers
        import rank_bm25
        import plotly
        print("✅ All dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install missing packages:")
        print("pip install sentence-transformers rank-bm25 plotly")
        return False
    
    # Step 3: Build flexible index
    print("\n🏗️ Building flexible index...")
    
    try:
        from app.core.flexible_indexer import build_index_from_emails
        
        # Build with mixedbread configuration (best balance of quality/speed)
        success = build_index_from_emails(
            raw_email_file,
            config_name="mixedbread_hybrid",
            output_path="data/flexible_index"
        )
        
        if success:
            print("✅ Flexible index built successfully!")
        else:
            print("❌ Failed to build flexible index")
            return False
            
    except Exception as e:
        logger.error(f"Index building failed: {e}")
        print(f"❌ Index building failed: {e}")
        return False
    
    # Step 4: Test the query engine
    print("\n🧪 Testing flexible query engine...")
    
    try:
        from app.core.flexible_query_engine import FlexibleQueryEngine
        
        engine = FlexibleQueryEngine()
        
        # Test loading experiment
        success = engine.load_experiment("mixedbread_hybrid")
        if not success:
            print("❌ Failed to load experiment configuration")
            return False
        
        print("✅ Successfully loaded experiment configuration")
        
        # Test query
        result = engine.query("test query", top_k=3)
        
        if 'error' in result:
            print(f"❌ Query test failed: {result['error']}")
            return False
        
        print(f"✅ Query test successful - found {len(result['results'])} results")
        print(f"   Total time: {result['timing']['total']:.3f}s")
        print(f"   Retrieval time: {result['timing']['retrieval']:.3f}s")
        
    except Exception as e:
        logger.error(f"Query engine test failed: {e}")
        print(f"❌ Query engine test failed: {e}")
        return False
    
    # Step 5: Create experiment launcher
    print("\n🎛️ Creating experiment launcher...")
    
    launcher_script = '''"""
Launch Flexible Email Intelligence Experiments
"""
import subprocess
import sys
from pathlib import Path

def main():
    print("🧪 Launching Email Intelligence Experimentation Lab...")
    
    # Launch experimental interface
    ui_script = str(Path(__file__).parent / "app" / "ui" / "experimental_interface.py")
    
    cmd = [
        sys.executable, "-m", "streamlit", "run", ui_script,
        "--server.port", "8506",
        "--server.headless", "true", 
        "--browser.gatherUsageStats", "false"
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
'''
    
    with open("launch_experiments.py", "w") as f:
        f.write(launcher_script)
    
    print("✅ Created launch_experiments.py")
    
    # Step 6: Success summary
    print("\n🎉 Flexible Email Intelligence System Setup Complete!")
    print("=" * 60)
    print()
    print("📚 What you can now do:")
    print("   • Test different embedding models (OpenAI, HuggingFace, Mixedbread)")
    print("   • Compare retrieval strategies (Vector, BM25, Hybrid)")
    print("   • Experiment with rerankers (Cross-encoder, BGE, etc.)")
    print("   • Benchmark different configurations")
    print("   • Switch models without rebuilding indexes")
    print()
    print("🚀 To start experimenting:")
    print("   python launch_experiments.py")
    print()
    print("🌐 Or use the original UI:")
    print("   python run_ui.py")
    print()
    print("Available experiments:")
    
    # List available experiments
    try:
        experiments = engine.list_experiments()
        for exp in experiments:
            config = engine.experiment_manager.get_experiment(exp)
            print(f"   • {exp}: {config.embedding_model.model_name} + {config.retrieval.strategy.value}")
    except:
        print("   • mixedbread_hybrid: High-quality local embeddings with hybrid search")
        print("   • openai_vector_only: OpenAI embeddings with vector search")
        print("   • bge_ensemble: BGE embeddings with ensemble retrieval")
    
    return True

def main():
    """Main setup function"""
    success = setup_flexible_system()
    
    if success:
        print("\n✅ Setup completed successfully!")
        return 0
    else:
        print("\n❌ Setup failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())