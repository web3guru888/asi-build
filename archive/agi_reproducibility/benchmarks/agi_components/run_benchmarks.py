#!/usr/bin/env python3
"""
AGI Component Benchmark Suite Runner

Main script for running the AGI Component Benchmark Suite.
Provides command-line interface for benchmarking AGI systems.

Usage:
    python run_benchmarks.py --system example --config default
    python run_benchmarks.py --system custom --config custom_config.json
    python run_benchmarks.py --help
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import BenchmarkConfig, DEFAULT_CONFIG
from core import AGIBenchmarkSuite
from tracking import ProgressTracker, SystemProfile
from analysis import BenchmarkAnalyzer
from examples.example_agi_system import ExampleAGISystem


def load_config(config_path: str) -> BenchmarkConfig:
    """Load configuration from file or use default"""
    if config_path == "default":
        return DEFAULT_CONFIG
    
    try:
        if os.path.exists(config_path):
            return BenchmarkConfig.load_config(config_path)
        else:
            print(f"Config file {config_path} not found, using default configuration")
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"Error loading config: {e}")
        print("Using default configuration")
        return DEFAULT_CONFIG


def create_system(system_type: str) -> object:
    """Create AGI system instance based on type"""
    if system_type == "example":
        return ExampleAGISystem()
    elif system_type == "custom":
        print("Please implement your custom AGI system by extending AGISystem class")
        print("See examples/example_agi_system.py for reference")
        return None
    else:
        print(f"Unknown system type: {system_type}")
        return None


def run_benchmark_suite(args):
    """Run the complete benchmark suite"""
    print("=" * 80)
    print("AGI Component Benchmark Suite")
    print("Measuring Genuine AGI Progress Across Core Cognitive Capabilities")
    print("=" * 80)
    
    # Load configuration
    print(f"\n📋 Loading configuration: {args.config}")
    config = load_config(args.config)
    
    # Validate configuration
    issues = config.validate_config()
    if issues:
        print("⚠️  Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        if input("Continue anyway? (y/N): ").lower() != 'y':
            return
    
    print(f"✅ Configuration loaded successfully")
    print(f"   Output directory: {config.output_dir}")
    print(f"   Max workers: {config.max_workers}")
    print(f"   Timeout: {config.timeout_seconds}s")
    
    # Create output directory
    os.makedirs(config.output_dir, exist_ok=True)
    
    # Initialize benchmark suite
    print(f"\n🔧 Initializing benchmark suite...")
    try:
        suite = AGIBenchmarkSuite(config)
        print("✅ Benchmark suite initialized")
    except Exception as e:
        print(f"❌ Error initializing benchmark suite: {e}")
        return
    
    # Create AGI system
    print(f"\n🤖 Creating AGI system: {args.system}")
    system = create_system(args.system)
    
    if system is None:
        print("❌ Failed to create AGI system")
        return
    
    print(f"✅ AGI system created: {system.name} v{system.version}")
    
    # Initialize progress tracking if enabled
    tracker = None
    if config.tracking_config.get("database", {}).get("enabled", True):
        print(f"\n📊 Initializing progress tracking...")
        try:
            tracker = ProgressTracker(config.tracking_config)
            
            # Register system
            system_profile = SystemProfile(
                system_id=f"{system.name}_{system.version}".lower().replace(" ", "_"),
                name=system.name,
                version=system.version,
                architecture_type=system.get_system_info().get("architecture_type", "unknown"),
                description=system.get_system_info().get("description", ""),
                tags=["benchmark_run", datetime.now().strftime("%Y-%m")],
                created_date=datetime.now()
            )
            
            tracker.register_system(system_profile)
            print("✅ Progress tracking initialized")
        except Exception as e:
            print(f"⚠️  Progress tracking initialization failed: {e}")
            tracker = None
    
    # Run benchmarks
    print(f"\n🚀 Starting benchmark execution...")
    print(f"   Enabled categories:")
    
    categories = []
    if config.run_reasoning: categories.append("Reasoning")
    if config.run_learning: categories.append("Learning") 
    if config.run_memory: categories.append("Memory")
    if config.run_creativity: categories.append("Creativity")
    if config.run_consciousness: categories.append("Consciousness")
    if config.run_symbolic: categories.append("Symbolic AI")
    if config.run_neural_symbolic: categories.append("Neural-Symbolic")
    if config.run_real_world: categories.append("Real-World")
    
    for category in categories:
        print(f"     ✓ {category}")
    
    try:
        start_time = datetime.now()
        results = suite.benchmark_system(system, save_results=True)
        end_time = datetime.now()
        
        print(f"\n🎉 Benchmark execution completed!")
        print(f"   Execution time: {(end_time - start_time).total_seconds():.1f} seconds")
        print(f"   Total tests: {len(results.results)}")
        print(f"   Successful tests: {sum(1 for r in results.results if r.success)}")
        print(f"   Success rate: {results.success_rate:.1f}%")
        print(f"   Average score: {results.average_score:.2f}")
        
    except Exception as e:
        print(f"❌ Benchmark execution failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Store results in tracker
    if tracker:
        print(f"\n💾 Storing results in progress tracker...")
        try:
            tracker.store_benchmark_results(results)
            print("✅ Results stored successfully")
        except Exception as e:
            print(f"⚠️  Error storing results: {e}")
    
    # Generate analysis if requested
    if args.analyze:
        print(f"\n📈 Generating analysis...")
        try:
            analyzer = BenchmarkAnalyzer(tracker)
            
            # Convert results to format expected by analyzer
            results_dict = {
                "system_name": results.system_name,
                "system_version": results.system_version,
                "start_time": results.start_time.isoformat(),
                "end_time": results.end_time.isoformat(),
                "summary": results.get_summary_stats(),
                "results": [
                    {
                        "benchmark_name": r.benchmark_name,
                        "test_name": r.test_name,
                        "score": r.score,
                        "normalized_score": r.normalized_score,
                        "success": r.success,
                        "execution_time": r.execution_time,
                        "error_message": r.error_message
                    }
                    for r in results.results
                ]
            }
            
            # Create capability profile
            profile = analyzer.create_capability_profile(results_dict)
            
            print(f"   📊 Capability Profile:")
            print(f"      Overall maturity: {profile.overall_maturity:.1f}")
            print(f"      Coverage completeness: {profile.coverage_completeness:.1f}%")
            print(f"      Strengths: {', '.join(profile.strengths)}")
            print(f"      Weaknesses: {', '.join(profile.weaknesses)}")
            
            # Generate comprehensive report
            if args.report:
                report = analyzer.generate_performance_report(
                    [results_dict], 
                    output_path=config.output_dir
                )
                
                if "report_path" in report:
                    print(f"   📄 Detailed report: {report['report_path']}")
                
                if "visualizations" in report and report["visualizations"]:
                    print(f"   📈 Visualizations created:")
                    for viz_path in report["visualizations"]:
                        print(f"      - {viz_path}")
            
        except Exception as e:
            print(f"⚠️  Analysis generation failed: {e}")
    
    # Show leaderboard if tracker available
    if tracker and args.leaderboard:
        print(f"\n🏆 Current Leaderboard (Top 5):")
        try:
            leaderboard = tracker.get_leaderboard(limit=5)
            
            if leaderboard:
                print(f"   {'Rank':<4} {'System':<20} {'Score':<8} {'Architecture':<15}")
                print(f"   {'-'*4} {'-'*20} {'-'*8} {'-'*15}")
                
                for entry in leaderboard:
                    print(f"   {entry['rank']:<4} {entry['name']:<20} {entry['score']:<8.1f} {entry['architecture_type']:<15}")
            else:
                print("   No systems in leaderboard yet")
                
        except Exception as e:
            print(f"⚠️  Error retrieving leaderboard: {e}")
    
    # Identify capability gaps
    if tracker and args.gaps:
        print(f"\n🎯 Capability Gap Analysis:")
        try:
            gaps = tracker.identify_capability_gaps(system_profile.system_id)
            
            if gaps:
                for gap in gaps[:3]:  # Show top 3 gaps
                    print(f"   📍 {gap.capability.title()}: {gap.gap_size:.1f} point gap ({gap.priority} priority)")
                    print(f"      Current: {gap.current_score:.1f}, Target: {gap.target_score:.1f}")
                    if gap.recommendations:
                        print(f"      💡 Recommendation: {gap.recommendations[0]}")
                    print()
            else:
                print("   🎉 No significant capability gaps identified!")
                
        except Exception as e:
            print(f"⚠️  Error analyzing capability gaps: {e}")
    
    print(f"\n✨ Benchmark run completed successfully!")
    print(f"   Results saved to: {config.output_dir}")
    
    if tracker:
        print(f"   Progress tracking database: {tracker.db_path}")
    
    print(f"\n🔍 Next steps:")
    print(f"   - Review detailed results in {config.output_dir}")
    print(f"   - Compare with other systems using the analysis tools")
    print(f"   - Use capability gap analysis to guide improvements")
    print(f"   - Run benchmarks regularly to track progress over time")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AGI Component Benchmark Suite - Measuring Genuine AGI Progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_benchmarks.py --system example
  python run_benchmarks.py --system example --config custom.json --analyze --report
  python run_benchmarks.py --system example --leaderboard --gaps
  
For more information, see README.md or visit:
https://github.com/kenny-agi/agi-reproducibility/benchmarks/agi_components
        """
    )
    
    parser.add_argument(
        "--system", 
        type=str, 
        default="example",
        choices=["example", "custom"],
        help="AGI system type to benchmark (default: example)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="default",
        help="Configuration file path or 'default' (default: default)"
    )
    
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Generate analysis after benchmarking"
    )
    
    parser.add_argument(
        "--report",
        action="store_true", 
        help="Generate comprehensive report (requires --analyze)"
    )
    
    parser.add_argument(
        "--leaderboard",
        action="store_true",
        help="Show current leaderboard"
    )
    
    parser.add_argument(
        "--gaps",
        action="store_true",
        help="Show capability gap analysis"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="AGI Component Benchmark Suite v1.0.0"
    )
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.report and not args.analyze:
        print("⚠️  --report requires --analyze flag")
        args.analyze = True
    
    try:
        run_benchmark_suite(args)
    except KeyboardInterrupt:
        print(f"\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()