/*
 * PLN Specialized Instruction Set Architecture
 * Custom instructions for probabilistic logic network operations
 * 
 * Features:
 * - Native PLN operations (deduction, induction, abduction)
 * - Vector truth value operations
 * - Memory management for truth values
 * - Performance monitoring instructions
 * - Parallel execution control
 * 
 * Author: PLN Accelerator Project
 * ISA: PLN-RISC (PLN Reduced Instruction Set Computer)
 */

#ifndef PLN_INSTRUCTION_SET_H
#define PLN_INSTRUCTION_SET_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// PLN Data Types
// ============================================================================

typedef struct {
    float strength;     // Truth value strength [0.0, 1.0]
    float confidence;   // Truth value confidence [0.0, 1.0]
} pln_truth_value_t;

typedef struct {
    uint32_t concept_id;
    pln_truth_value_t truth_value;
    uint32_t timestamp;
    uint16_t flags;
} pln_concept_t;

typedef struct {
    uint32_t source_id;
    uint32_t target_id;
    pln_truth_value_t link_strength;
    uint8_t link_type;
    uint8_t direction;
} pln_link_t;

// ============================================================================
// PLN Instruction Format
// ============================================================================

// 32-bit instruction format:
// [31:26] - Opcode (6 bits)
// [25:21] - Rs1 (source register 1)
// [20:16] - Rs2 (source register 2)
// [15:11] - Rd (destination register)
// [10:0]  - Immediate/Function code

typedef enum {
    // Basic PLN Operations (0x00-0x0F)
    PLN_OP_DEDUCTION    = 0x00,
    PLN_OP_INDUCTION    = 0x01,
    PLN_OP_ABDUCTION    = 0x02,
    PLN_OP_REVISION     = 0x03,
    PLN_OP_CONJUNCTION  = 0x04,
    PLN_OP_DISJUNCTION  = 0x05,
    PLN_OP_NEGATION     = 0x06,
    PLN_OP_SIMILARITY   = 0x07,
    PLN_OP_COMPARISON   = 0x08,
    PLN_OP_INHERITANCE  = 0x09,
    PLN_OP_IMPLICATION  = 0x0A,
    PLN_OP_EQUIVALENCE  = 0x0B,
    
    // Memory Operations (0x10-0x1F)
    PLN_OP_LOAD_TV      = 0x10,    // Load truth value
    PLN_OP_STORE_TV     = 0x11,    // Store truth value
    PLN_OP_LOAD_CONCEPT = 0x12,    // Load concept
    PLN_OP_STORE_CONCEPT= 0x13,    // Store concept
    PLN_OP_PREFETCH     = 0x14,    // Prefetch data
    PLN_OP_CACHE_FLUSH  = 0x15,    // Flush cache
    PLN_OP_MEMORY_FENCE = 0x16,    // Memory fence
    
    // Vector Operations (0x20-0x2F)
    PLN_OP_VEC_DEDUCTION= 0x20,    // Vector deduction
    PLN_OP_VEC_AND      = 0x21,    // Vector conjunction
    PLN_OP_VEC_OR       = 0x22,    // Vector disjunction
    PLN_OP_VEC_NOT      = 0x23,    // Vector negation
    PLN_OP_VEC_REDUCE   = 0x24,    // Vector reduction
    PLN_OP_VEC_BROADCAST= 0x25,    // Broadcast value
    PLN_OP_VEC_GATHER   = 0x26,    // Gather operation
    PLN_OP_VEC_SCATTER  = 0x27,    // Scatter operation
    
    // Propagation Operations (0x30-0x3F)
    PLN_OP_PROPAGATE_FWD= 0x30,    // Forward propagation
    PLN_OP_PROPAGATE_BWD= 0x31,    // Backward propagation
    PLN_OP_PROPAGATE_BI = 0x32,    // Bidirectional propagation
    PLN_OP_WAVE_FRONT   = 0x33,    // Wave-front propagation
    PLN_OP_CONSTRAINT   = 0x34,    // Constraint propagation
    PLN_OP_SPREAD_ACT   = 0x35,    // Spreading activation
    
    // Control Operations (0x40-0x4F)
    PLN_OP_BRANCH_TV    = 0x40,    // Branch on truth value
    PLN_OP_CALL_PLN     = 0x41,    // Call PLN function
    PLN_OP_RETURN_PLN   = 0x42,    // Return from PLN function
    PLN_OP_PARALLEL_FOR = 0x43,    // Parallel for loop
    PLN_OP_BARRIER      = 0x44,    // Synchronization barrier
    PLN_OP_ATOMIC_TV    = 0x45,    // Atomic truth value operation
    
    // Performance & Debug (0x50-0x5F)
    PLN_OP_PERF_COUNT   = 0x50,    // Performance counter
    PLN_OP_TRACE_START  = 0x51,    // Start execution trace
    PLN_OP_TRACE_STOP   = 0x52,    // Stop execution trace
    PLN_OP_PROFILE      = 0x53,    // Profile operation
    PLN_OP_DEBUG_BREAK  = 0x54,    // Debug breakpoint
    
    // Quantum Operations (0x60-0x6F)
    PLN_OP_QUANTUM_INIT = 0x60,    // Initialize quantum circuit
    PLN_OP_QUANTUM_EXEC = 0x61,    // Execute quantum operation
    PLN_OP_QUANTUM_MEAS = 0x62,    // Quantum measurement
    PLN_OP_QUANTUM_SYNC = 0x63,    // Sync quantum-classical
} pln_opcode_t;

// ============================================================================
// PLN Register File
// ============================================================================

#define PLN_NUM_REGISTERS 32
#define PLN_NUM_VECTOR_REGISTERS 16
#define PLN_VECTOR_WIDTH 8  // 8 truth values per vector register

typedef struct {
    pln_truth_value_t scalar_regs[PLN_NUM_REGISTERS];
    pln_truth_value_t vector_regs[PLN_NUM_VECTOR_REGISTERS][PLN_VECTOR_WIDTH];
    uint32_t concept_regs[PLN_NUM_REGISTERS];  // Concept ID registers
    uint32_t control_regs[16];                 // Control/status registers
} pln_register_file_t;

// Control Register Definitions
#define PLN_REG_STATUS      0   // Status register
#define PLN_REG_CONFIG      1   // Configuration register
#define PLN_REG_PERF_COUNT  2   // Performance counter
#define PLN_REG_ERROR       3   // Error status
#define PLN_REG_CACHE_CTRL  4   // Cache control
#define PLN_REG_QUANTUM_ST  5   // Quantum state

// ============================================================================
// PLN Instruction Encoding/Decoding
// ============================================================================

typedef struct {
    uint8_t opcode;
    uint8_t rs1;
    uint8_t rs2;
    uint8_t rd;
    uint16_t immediate;
    uint8_t function_code;
} pln_instruction_t;

static inline uint32_t pln_encode_instruction(pln_instruction_t *inst) {
    return ((uint32_t)inst->opcode << 26) |
           ((uint32_t)inst->rs1 << 21) |
           ((uint32_t)inst->rs2 << 16) |
           ((uint32_t)inst->rd << 11) |
           ((uint32_t)inst->immediate & 0x7FF);
}

static inline pln_instruction_t pln_decode_instruction(uint32_t encoded) {
    pln_instruction_t inst;
    inst.opcode = (encoded >> 26) & 0x3F;
    inst.rs1 = (encoded >> 21) & 0x1F;
    inst.rs2 = (encoded >> 16) & 0x1F;
    inst.rd = (encoded >> 11) & 0x1F;
    inst.immediate = encoded & 0x7FF;
    inst.function_code = encoded & 0x7F;
    return inst;
}

// ============================================================================
// PLN Assembly Macros
// ============================================================================

#define PLN_DEDUCTION(rd, rs1, rs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_DEDUCTION, rs1, rs2, rd, 0, 0})

#define PLN_INDUCTION(rd, rs1, rs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_INDUCTION, rs1, rs2, rd, 0, 0})

#define PLN_ABDUCTION(rd, rs1, rs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_ABDUCTION, rs1, rs2, rd, 0, 0})

#define PLN_AND(rd, rs1, rs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_CONJUNCTION, rs1, rs2, rd, 0, 0})

#define PLN_OR(rd, rs1, rs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_DISJUNCTION, rs1, rs2, rd, 0, 0})

#define PLN_NOT(rd, rs1) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_NEGATION, rs1, 0, rd, 0, 0})

#define PLN_LOAD_TV(rd, rs1, offset) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_LOAD_TV, rs1, 0, rd, offset, 0})

#define PLN_STORE_TV(rs1, rs2, offset) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_STORE_TV, rs1, rs2, 0, offset, 0})

#define PLN_PROPAGATE_FWD(rd, rs1, depth) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_PROPAGATE_FWD, rs1, 0, rd, depth, 0})

#define PLN_VEC_AND(vrd, vrs1, vrs2) \
    pln_encode_instruction(&(pln_instruction_t){PLN_OP_VEC_AND, vrs1, vrs2, vrd, 0, 0})

// ============================================================================
// PLN Instruction Execution Functions
// ============================================================================

// Execute single PLN instruction
typedef enum {
    PLN_EXEC_SUCCESS = 0,
    PLN_EXEC_INVALID_OPCODE,
    PLN_EXEC_INVALID_REGISTER,
    PLN_EXEC_MEMORY_ERROR,
    PLN_EXEC_DIVISION_BY_ZERO,
    PLN_EXEC_QUANTUM_ERROR
} pln_exec_result_t;

pln_exec_result_t pln_execute_instruction(uint32_t instruction, 
                                         pln_register_file_t *registers);

// PLN-specific arithmetic operations
pln_truth_value_t pln_deduction(pln_truth_value_t premise1, 
                               pln_truth_value_t premise2);
pln_truth_value_t pln_induction(pln_truth_value_t evidence1, 
                               pln_truth_value_t evidence2);
pln_truth_value_t pln_abduction(pln_truth_value_t observation, 
                               pln_truth_value_t hypothesis);
pln_truth_value_t pln_conjunction(pln_truth_value_t tv1, 
                                 pln_truth_value_t tv2);
pln_truth_value_t pln_disjunction(pln_truth_value_t tv1, 
                                 pln_truth_value_t tv2);
pln_truth_value_t pln_negation(pln_truth_value_t tv);
pln_truth_value_t pln_revision(pln_truth_value_t old_tv, 
                              pln_truth_value_t new_tv);

// Vector operations
void pln_vector_deduction(pln_truth_value_t *result, 
                         pln_truth_value_t *vec1, 
                         pln_truth_value_t *vec2, 
                         int length);
void pln_vector_conjunction(pln_truth_value_t *result, 
                           pln_truth_value_t *vec1, 
                           pln_truth_value_t *vec2, 
                           int length);
pln_truth_value_t pln_vector_reduce(pln_truth_value_t *vector, 
                                   int length, 
                                   pln_opcode_t operation);

// ============================================================================
// PLN Compiler Interface
// ============================================================================

typedef struct {
    char mnemonic[16];
    pln_opcode_t opcode;
    int num_operands;
    bool is_vector;
    bool is_memory;
    int latency_cycles;
    float power_consumption;
} pln_instruction_info_t;

extern const pln_instruction_info_t pln_instruction_table[];

// Compile PLN assembly to binary
int pln_compile_assembly(const char *assembly_code, 
                        uint32_t *binary_output, 
                        int max_instructions);

// Disassemble binary to PLN assembly
int pln_disassemble_binary(uint32_t *binary_code, 
                          char *assembly_output, 
                          int num_instructions);

// ============================================================================
// PLN Performance Optimization Hints
// ============================================================================

typedef struct {
    bool enable_vector_optimization;
    bool enable_memory_coalescing;
    bool enable_instruction_fusion;
    bool enable_branch_prediction;
    bool enable_quantum_acceleration;
    int cache_prefetch_distance;
    int parallel_execution_width;
} pln_optimization_hints_t;

void pln_set_optimization_hints(pln_optimization_hints_t *hints);
void pln_get_performance_counters(uint64_t *counters, int num_counters);

// ============================================================================
// PLN Debugging and Profiling
// ============================================================================

typedef struct {
    uint64_t instruction_count;
    uint64_t cycle_count;
    uint64_t cache_hits;
    uint64_t cache_misses;
    uint64_t memory_accesses;
    uint64_t quantum_operations;
    float average_truth_value_strength;
    float average_truth_value_confidence;
} pln_execution_stats_t;

void pln_start_profiling(void);
void pln_stop_profiling(pln_execution_stats_t *stats);
void pln_print_execution_trace(FILE *output);

// ============================================================================
// PLN Quantum Integration
// ============================================================================

typedef enum {
    PLN_QUANTUM_DEDUCTION,
    PLN_QUANTUM_INDUCTION,
    PLN_QUANTUM_ABDUCTION,
    PLN_QUANTUM_SIMILARITY,
    PLN_QUANTUM_SUPERPOSITION
} pln_quantum_operation_t;

int pln_quantum_execute(pln_quantum_operation_t operation,
                       pln_truth_value_t *inputs,
                       pln_truth_value_t *outputs,
                       int num_qubits);

// ============================================================================
// PLN Hardware Abstraction
// ============================================================================

typedef enum {
    PLN_HARDWARE_FPGA,
    PLN_HARDWARE_ASIC,
    PLN_HARDWARE_GPU,
    PLN_HARDWARE_QUANTUM,
    PLN_HARDWARE_HYBRID
} pln_hardware_type_t;

typedef struct {
    pln_hardware_type_t type;
    int processing_units;
    int memory_channels;
    int quantum_qubits;
    float clock_frequency_mhz;
    int cache_size_kb;
} pln_hardware_config_t;

int pln_initialize_hardware(pln_hardware_config_t *config);
int pln_shutdown_hardware(void);
int pln_get_hardware_status(pln_hardware_config_t *status);

// ============================================================================
// PLN Error Handling
// ============================================================================

typedef enum {
    PLN_ERROR_NONE = 0,
    PLN_ERROR_INVALID_TRUTH_VALUE,
    PLN_ERROR_CONCEPT_NOT_FOUND,
    PLN_ERROR_MEMORY_ALLOCATION,
    PLN_ERROR_HARDWARE_FAILURE,
    PLN_ERROR_QUANTUM_DECOHERENCE,
    PLN_ERROR_TIMEOUT,
    PLN_ERROR_SYNCHRONIZATION
} pln_error_code_t;

const char* pln_get_error_string(pln_error_code_t error);
void pln_set_error_handler(void (*handler)(pln_error_code_t));

// ============================================================================
// Example PLN Programs
// ============================================================================

// Simple deduction chain: A->B, B->C, therefore A->C
static const uint32_t pln_example_deduction[] = {
    PLN_LOAD_TV(1, 0, 0),      // Load A->B truth value
    PLN_LOAD_TV(2, 0, 1),      // Load B->C truth value
    PLN_DEDUCTION(3, 1, 2),    // Deduce A->C
    PLN_STORE_TV(3, 0, 2),     // Store result
};

// Vector truth value processing
static const uint32_t pln_example_vector[] = {
    PLN_VEC_AND(0, 1, 2),      // Vector conjunction
    PLN_VEC_REDUCE(3, 0, 0),   // Reduce to scalar
};

// Parallel propagation
static const uint32_t pln_example_propagation[] = {
    PLN_LOAD_CONCEPT(1, 0, 0), // Load source concept
    PLN_PROPAGATE_FWD(2, 1, 5), // Forward propagate depth 5
    PLN_BARRIER(0, 0, 0),      // Wait for completion
};

#endif // PLN_INSTRUCTION_SET_H