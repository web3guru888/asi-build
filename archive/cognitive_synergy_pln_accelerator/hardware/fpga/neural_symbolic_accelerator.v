/*
 * Neural-Symbolic Integration Accelerator
 * Hardware acceleration for hybrid neural-symbolic AI systems
 * 
 * Features:
 * - Neural network inference acceleration
 * - Symbolic reasoning integration  
 * - PLN-neural interface
 * - Attention mechanism hardware
 * - Knowledge graph embedding
 * - Real-time neural-symbolic fusion
 * 
 * Author: PLN Accelerator Project
 * Target: High-performance neural-symbolic computing
 */

module neural_symbolic_accelerator #(
    parameter NEURAL_WIDTH = 512,        // Neural activation width
    parameter SYMBOLIC_WIDTH = 64,       // Symbolic truth value width  
    parameter NUM_NEURONS = 1024,        // Number of neurons per layer
    parameter NUM_LAYERS = 8,            // Number of neural layers
    parameter NUM_CONCEPTS = 8192,       // Number of symbolic concepts
    parameter ATTENTION_HEADS = 16,      // Multi-head attention
    parameter EMBEDDING_DIM = 256        // Knowledge graph embedding dimension
)(
    input wire clk,
    input wire rst_n,
    
    // Neural Network Interface
    input wire [NEURAL_WIDTH-1:0] neural_input [NUM_NEURONS-1:0],
    output reg [NEURAL_WIDTH-1:0] neural_output [NUM_NEURONS-1:0],
    input wire neural_valid,
    output reg neural_ready,
    
    // Symbolic Reasoning Interface
    input wire [SYMBOLIC_WIDTH-1:0] symbolic_input [NUM_CONCEPTS-1:0],
    output reg [SYMBOLIC_WIDTH-1:0] symbolic_output [NUM_CONCEPTS-1:0],
    input wire symbolic_valid,
    output reg symbolic_ready,
    
    // Neural-Symbolic Fusion Control
    input wire fusion_enable,
    input wire [2:0] fusion_mode,
    input wire [15:0] fusion_strength,
    
    // Knowledge Graph Interface
    input wire [EMBEDDING_DIM-1:0] concept_embeddings [NUM_CONCEPTS-1:0],
    input wire [31:0] concept_relations [NUM_CONCEPTS-1:0][15:0], // Up to 16 relations per concept
    input wire embeddings_valid,
    
    // Performance Monitoring
    output reg [31:0] neural_ops_per_second,
    output reg [31:0] symbolic_ops_per_second,
    output reg [31:0] fusion_efficiency,
    output reg processing_complete
);

// Fusion Modes
localparam FUSION_ATTENTION = 3'b000;     // Attention-based fusion
localparam FUSION_GATING = 3'b001;        // Gating mechanism
localparam FUSION_RESIDUAL = 3'b010;      // Residual connections
localparam FUSION_CROSS_MODAL = 3'b011;   // Cross-modal interaction
localparam FUSION_GRAPH_NEURAL = 3'b100;  // Graph neural networks

// Neural Processing Pipeline
reg [NEURAL_WIDTH-1:0] neural_layer_outputs [NUM_LAYERS-1:0][NUM_NEURONS-1:0];
reg [NEURAL_WIDTH-1:0] neural_weights [NUM_LAYERS-1:0][NUM_NEURONS-1:0][NUM_NEURONS-1:0];
reg [NEURAL_WIDTH-1:0] neural_biases [NUM_LAYERS-1:0][NUM_NEURONS-1:0];

// Symbolic Processing Pipeline  
reg [SYMBOLIC_WIDTH-1:0] symbolic_memory [NUM_CONCEPTS-1:0];
reg [31:0] symbolic_concept_ids [NUM_CONCEPTS-1:0];
reg symbolic_concept_valid [NUM_CONCEPTS-1:0];

// Attention Mechanism
reg [NEURAL_WIDTH-1:0] attention_queries [ATTENTION_HEADS-1:0][NUM_NEURONS-1:0];
reg [NEURAL_WIDTH-1:0] attention_keys [ATTENTION_HEADS-1:0][NUM_CONCEPTS-1:0];
reg [NEURAL_WIDTH-1:0] attention_values [ATTENTION_HEADS-1:0][NUM_CONCEPTS-1:0];
reg [31:0] attention_weights [ATTENTION_HEADS-1:0][NUM_NEURONS-1:0][NUM_CONCEPTS-1:0];

// Knowledge Graph Embeddings
reg [EMBEDDING_DIM-1:0] kg_embeddings [NUM_CONCEPTS-1:0];
reg [EMBEDDING_DIM-1:0] neural_projections [NUM_NEURONS-1:0];

// Fusion Interface
reg [NEURAL_WIDTH-1:0] fused_neural_features [NUM_NEURONS-1:0];
reg [SYMBOLIC_WIDTH-1:0] fused_symbolic_features [NUM_CONCEPTS-1:0];

// Processing State Machine
reg [3:0] processing_state;
reg [15:0] layer_counter;
reg [15:0] concept_counter;

localparam STATE_IDLE = 4'h0;
localparam STATE_NEURAL_FORWARD = 4'h1;
localparam STATE_SYMBOLIC_REASONING = 4'h2;
localparam STATE_ATTENTION_COMPUTE = 4'h3;
localparam STATE_FUSION = 4'h4;
localparam STATE_OUTPUT = 4'h5;

// Performance Counters
reg [31:0] neural_operations;
reg [31:0] symbolic_operations;
reg [31:0] cycle_counter;
reg [31:0] last_neural_ops;
reg [31:0] last_symbolic_ops;

// ============================================================================
// Neural Network Forward Pass
// ============================================================================

// Parallel neural processing units
genvar layer_idx, neuron_idx;
generate
    for (layer_idx = 0; layer_idx < NUM_LAYERS; layer_idx = layer_idx + 1) begin : neural_layers
        for (neuron_idx = 0; neuron_idx < NUM_NEURONS; neuron_idx = neuron_idx + 1) begin : neurons
            
            reg [NEURAL_WIDTH-1:0] neuron_accumulator;
            reg [NEURAL_WIDTH-1:0] neuron_activation;
            reg neuron_processing;
            
            always @(posedge clk) begin
                if (!rst_n) begin
                    neuron_accumulator <= 0;
                    neuron_activation <= 0;
                    neuron_processing <= 0;
                end else if (processing_state == STATE_NEURAL_FORWARD && 
                           layer_counter == layer_idx) begin
                    
                    neuron_processing <= 1;
                    neuron_accumulator <= neural_biases[layer_idx][neuron_idx];
                    
                    // Matrix multiplication with previous layer
                    for (integer i = 0; i < NUM_NEURONS; i = i + 1) begin
                        if (layer_idx == 0) begin
                            neuron_accumulator <= neuron_accumulator + 
                                neural_input[i] * neural_weights[layer_idx][neuron_idx][i];
                        end else begin
                            neuron_accumulator <= neuron_accumulator + 
                                neural_layer_outputs[layer_idx-1][i] * 
                                neural_weights[layer_idx][neuron_idx][i];
                        end
                    end
                    
                    // Apply activation function (ReLU)
                    neuron_activation <= (neuron_accumulator[NEURAL_WIDTH-1] == 0) ? 
                                       neuron_accumulator : 0;
                    
                    neural_layer_outputs[layer_idx][neuron_idx] <= neuron_activation;
                    neural_operations <= neural_operations + 1;
                    
                end else begin
                    neuron_processing <= 0;
                end
            end
        end
    end
endgenerate

// ============================================================================
// Symbolic Reasoning Engine
// ============================================================================

reg [3:0] symbolic_state [NUM_CONCEPTS-1:0];
reg [SYMBOLIC_WIDTH-1:0] symbolic_inference_results [NUM_CONCEPTS-1:0];

localparam SYM_IDLE = 4'h0;
localparam SYM_LOAD = 4'h1;
localparam SYM_INFER = 4'h2;
localparam SYM_PROPAGATE = 4'h3;
localparam SYM_COMPLETE = 4'h4;

genvar concept_idx;
generate
    for (concept_idx = 0; concept_idx < NUM_CONCEPTS; concept_idx = concept_idx + 1) begin : symbolic_processors
        
        always @(posedge clk) begin
            if (!rst_n) begin
                symbolic_state[concept_idx] <= SYM_IDLE;
                symbolic_inference_results[concept_idx] <= 0;
            end else if (processing_state == STATE_SYMBOLIC_REASONING) begin
                case (symbolic_state[concept_idx])
                    SYM_IDLE: begin
                        if (symbolic_valid) begin
                            symbolic_memory[concept_idx] <= symbolic_input[concept_idx];
                            symbolic_state[concept_idx] <= SYM_LOAD;
                        end
                    end
                    
                    SYM_LOAD: begin
                        // Load related concepts for inference
                        symbolic_state[concept_idx] <= SYM_INFER;
                    end
                    
                    SYM_INFER: begin
                        // Perform PLN inference
                        symbolic_inference_results[concept_idx] <= 
                            perform_symbolic_inference(symbolic_memory[concept_idx], concept_idx);
                        symbolic_state[concept_idx] <= SYM_PROPAGATE;
                        symbolic_operations <= symbolic_operations + 1;
                    end
                    
                    SYM_PROPAGATE: begin
                        // Propagate results to related concepts
                        symbolic_output[concept_idx] <= symbolic_inference_results[concept_idx];
                        symbolic_state[concept_idx] <= SYM_COMPLETE;
                    end
                    
                    SYM_COMPLETE: begin
                        symbolic_state[concept_idx] <= SYM_IDLE;
                    end
                    
                    default: symbolic_state[concept_idx] <= SYM_IDLE;
                endcase
            end
        end
        
        // Symbolic inference function
        function [SYMBOLIC_WIDTH-1:0] perform_symbolic_inference;
            input [SYMBOLIC_WIDTH-1:0] input_tv;
            input [31:0] concept_id;
            reg [31:0] strength, confidence;
            reg [31:0] inferred_strength, inferred_confidence;
            begin
                strength = input_tv[63:32];
                confidence = input_tv[31:0];
                
                // Simple symbolic inference rule
                inferred_strength = strength + (strength >> 2); // 25% boost
                inferred_confidence = confidence - (confidence >> 3); // Slight confidence reduction
                
                // Clamp values
                if (inferred_strength > 32'hFFFFFFFF) inferred_strength = 32'hFFFFFFFF;
                if (inferred_confidence > 32'hFFFFFFFF) inferred_confidence = 32'hFFFFFFFF;
                
                perform_symbolic_inference = {inferred_strength, inferred_confidence};
            end
        endfunction
    end
endgenerate

// ============================================================================
// Multi-Head Attention Mechanism
// ============================================================================

genvar head_idx, query_idx, key_idx;
generate
    for (head_idx = 0; head_idx < ATTENTION_HEADS; head_idx = head_idx + 1) begin : attention_heads
        
        reg [31:0] attention_scores [NUM_NEURONS-1:0][NUM_CONCEPTS-1:0];
        reg [31:0] attention_sum [NUM_NEURONS-1:0];
        reg [NEURAL_WIDTH-1:0] attended_output [NUM_NEURONS-1:0];
        
        for (query_idx = 0; query_idx < NUM_NEURONS; query_idx = query_idx + 1) begin : attention_queries_gen
            for (key_idx = 0; key_idx < NUM_CONCEPTS; key_idx = key_idx + 1) begin : attention_computation
                
                always @(posedge clk) begin
                    if (!rst_n) begin
                        attention_scores[query_idx][key_idx] <= 0;
                        attention_weights[head_idx][query_idx][key_idx] <= 0;
                    end else if (processing_state == STATE_ATTENTION_COMPUTE) begin
                        
                        // Compute attention score (simplified dot product)
                        attention_scores[query_idx][key_idx] <= 
                            dot_product_neural_symbolic(
                                attention_queries[head_idx][query_idx],
                                attention_keys[head_idx][key_idx]);
                        
                        // Softmax normalization (simplified)
                        attention_weights[head_idx][query_idx][key_idx] <= 
                            attention_scores[query_idx][key_idx]; // Simplified - real softmax needed
                        
                    end
                end
                
                // Dot product function for neural-symbolic attention
                function [31:0] dot_product_neural_symbolic;
                    input [NEURAL_WIDTH-1:0] neural_vec;
                    input [NEURAL_WIDTH-1:0] symbolic_vec;
                    reg [63:0] product_sum;
                    integer i;
                    begin
                        product_sum = 0;
                        for (i = 0; i < 16; i = i + 1) begin // Simplified computation
                            product_sum = product_sum + 
                                (neural_vec[i*32 +: 32] * symbolic_vec[i*32 +: 32]);
                        end
                        dot_product_neural_symbolic = product_sum[31:0];
                    end
                endfunction
            end
        end
        
        // Compute attended output
        for (query_idx = 0; query_idx < NUM_NEURONS; query_idx = query_idx + 1) begin : attended_output_gen
            always @(posedge clk) begin
                if (!rst_n) begin
                    attended_output[query_idx] <= 0;
                end else if (processing_state == STATE_ATTENTION_COMPUTE) begin
                    attended_output[query_idx] <= 0;
                    
                    // Weighted sum of values
                    for (integer k = 0; k < NUM_CONCEPTS; k = k + 1) begin
                        attended_output[query_idx] <= attended_output[query_idx] + 
                            (attention_weights[head_idx][query_idx][k] * 
                             attention_values[head_idx][k]) >> 16; // Scale down
                    end
                end
            end
        end
    end
endgenerate

// ============================================================================
// Neural-Symbolic Fusion Engine
// ============================================================================

genvar fusion_idx;
generate
    for (fusion_idx = 0; fusion_idx < NUM_NEURONS; fusion_idx = fusion_idx + 1) begin : fusion_units
        
        reg [NEURAL_WIDTH-1:0] gating_signal;
        reg [NEURAL_WIDTH-1:0] residual_connection;
        reg [NEURAL_WIDTH-1:0] cross_modal_feature;
        
        always @(posedge clk) begin
            if (!rst_n) begin
                fused_neural_features[fusion_idx] <= 0;
                gating_signal <= 0;
                residual_connection <= 0;
                cross_modal_feature <= 0;
            end else if (processing_state == STATE_FUSION && fusion_enable) begin
                
                case (fusion_mode)
                    FUSION_ATTENTION: begin
                        // Use attention mechanism for fusion
                        fused_neural_features[fusion_idx] <= 
                            neural_layer_outputs[NUM_LAYERS-1][fusion_idx] + 
                            (attended_output[fusion_idx] >> 2); // 25% symbolic contribution
                    end
                    
                    FUSION_GATING: begin
                        // Gating mechanism
                        gating_signal <= compute_gating_signal(
                            neural_layer_outputs[NUM_LAYERS-1][fusion_idx],
                            project_symbolic_to_neural(fusion_idx));
                        
                        fused_neural_features[fusion_idx] <= 
                            (neural_layer_outputs[NUM_LAYERS-1][fusion_idx] * gating_signal) >> 16;
                    end
                    
                    FUSION_RESIDUAL: begin
                        // Residual connections
                        residual_connection <= 
                            project_symbolic_to_neural(fusion_idx);
                        
                        fused_neural_features[fusion_idx] <= 
                            neural_layer_outputs[NUM_LAYERS-1][fusion_idx] + residual_connection;
                    end
                    
                    FUSION_CROSS_MODAL: begin
                        // Cross-modal interaction
                        cross_modal_feature <= cross_modal_interaction(
                            neural_layer_outputs[NUM_LAYERS-1][fusion_idx],
                            fusion_idx);
                        
                        fused_neural_features[fusion_idx] <= cross_modal_feature;
                    end
                    
                    default: begin
                        fused_neural_features[fusion_idx] <= 
                            neural_layer_outputs[NUM_LAYERS-1][fusion_idx];
                    end
                endcase
            end
        end
        
        // Gating signal computation
        function [NEURAL_WIDTH-1:0] compute_gating_signal;
            input [NEURAL_WIDTH-1:0] neural_feature;
            input [NEURAL_WIDTH-1:0] symbolic_feature;
            reg [NEURAL_WIDTH-1:0] gate;
            begin
                // Simplified gating: sigmoid-like function
                gate = (neural_feature + symbolic_feature) >> 1;
                compute_gating_signal = (gate[NEURAL_WIDTH-1] == 0) ? gate : 0;
            end
        endfunction
        
        // Project symbolic features to neural space
        function [NEURAL_WIDTH-1:0] project_symbolic_to_neural;
            input [31:0] neuron_id;
            reg [NEURAL_WIDTH-1:0] projection;
            reg [31:0] concept_id;
            begin
                concept_id = neuron_id % NUM_CONCEPTS;
                // Simple projection: replicate symbolic truth value
                projection = {8{symbolic_memory[concept_id]}};
                project_symbolic_to_neural = projection;
            end
        endfunction
        
        // Cross-modal interaction
        function [NEURAL_WIDTH-1:0] cross_modal_interaction;
            input [NEURAL_WIDTH-1:0] neural_feature;
            input [31:0] neuron_id;
            reg [NEURAL_WIDTH-1:0] interaction;
            reg [31:0] concept_id;
            reg [SYMBOLIC_WIDTH-1:0] related_symbolic;
            begin
                concept_id = neuron_id % NUM_CONCEPTS;
                related_symbolic = symbolic_memory[concept_id];
                
                // Element-wise multiplication with broadcasting
                interaction = neural_feature & {8{related_symbolic[31:0]}};
                cross_modal_interaction = interaction;
            end
        endfunction
    end
endgenerate

// ============================================================================
// Knowledge Graph Integration
// ============================================================================

reg [EMBEDDING_DIM-1:0] graph_embeddings [NUM_CONCEPTS-1:0];
reg [31:0] graph_adjacency [NUM_CONCEPTS-1:0][15:0]; // Up to 16 neighbors

always @(posedge clk) begin
    if (!rst_n) begin
        for (integer i = 0; i < NUM_CONCEPTS; i = i + 1) begin
            graph_embeddings[i] <= 0;
            for (integer j = 0; j < 16; j = j + 1) begin
                graph_adjacency[i][j] <= 0;
            end
        end
    end else if (embeddings_valid) begin
        // Load knowledge graph embeddings
        for (integer i = 0; i < NUM_CONCEPTS; i = i + 1) begin
            graph_embeddings[i] <= concept_embeddings[i];
            for (integer j = 0; j < 16; j = j + 1) begin
                graph_adjacency[i][j] <= concept_relations[i][j];
            end
        end
    end
end

// Graph neural network processing
genvar gnn_idx;
generate
    for (gnn_idx = 0; gnn_idx < NUM_CONCEPTS; gnn_idx = gnn_idx + 1) begin : gnn_processors
        
        reg [EMBEDDING_DIM-1:0] aggregated_embedding;
        reg [EMBEDDING_DIM-1:0] updated_embedding;
        
        always @(posedge clk) begin
            if (!rst_n) begin
                aggregated_embedding <= 0;
                updated_embedding <= 0;
            end else if (fusion_mode == FUSION_GRAPH_NEURAL) begin
                
                // Aggregate neighbor embeddings
                aggregated_embedding <= graph_embeddings[gnn_idx];
                
                for (integer neighbor = 0; neighbor < 16; neighbor = neighbor + 1) begin
                    if (graph_adjacency[gnn_idx][neighbor] != 0) begin
                        aggregated_embedding <= aggregated_embedding + 
                            (graph_embeddings[graph_adjacency[gnn_idx][neighbor]] >> 4);
                    end
                end
                
                // Update embedding (simple linear transformation)
                updated_embedding <= aggregated_embedding + 
                    (graph_embeddings[gnn_idx] >> 2);
                
                graph_embeddings[gnn_idx] <= updated_embedding;
            end
        end
    end
endgenerate

// ============================================================================
// Main Processing State Machine
// ============================================================================

always @(posedge clk) begin
    if (!rst_n) begin
        processing_state <= STATE_IDLE;
        layer_counter <= 0;
        concept_counter <= 0;
        neural_ready <= 1;
        symbolic_ready <= 1;
        processing_complete <= 0;
    end else begin
        case (processing_state)
            STATE_IDLE: begin
                if (neural_valid || symbolic_valid) begin
                    processing_state <= STATE_NEURAL_FORWARD;
                    layer_counter <= 0;
                    concept_counter <= 0;
                    neural_ready <= 0;
                    symbolic_ready <= 0;
                    processing_complete <= 0;
                end
            end
            
            STATE_NEURAL_FORWARD: begin
                if (layer_counter < NUM_LAYERS) begin
                    layer_counter <= layer_counter + 1;
                end else begin
                    processing_state <= STATE_SYMBOLIC_REASONING;
                    concept_counter <= 0;
                end
            end
            
            STATE_SYMBOLIC_REASONING: begin
                if (concept_counter < NUM_CONCEPTS) begin
                    concept_counter <= concept_counter + 1;
                end else begin
                    processing_state <= STATE_ATTENTION_COMPUTE;
                end
            end
            
            STATE_ATTENTION_COMPUTE: begin
                // Attention computation takes fixed cycles
                processing_state <= STATE_FUSION;
            end
            
            STATE_FUSION: begin
                if (fusion_enable) begin
                    // Perform neural-symbolic fusion
                    for (integer i = 0; i < NUM_NEURONS; i = i + 1) begin
                        neural_output[i] <= fused_neural_features[i];
                    end
                    
                    for (integer i = 0; i < NUM_CONCEPTS; i = i + 1) begin
                        fused_symbolic_features[i] <= 
                            enhance_symbolic_with_neural(symbolic_inference_results[i], i);
                        symbolic_output[i] <= fused_symbolic_features[i];
                    end
                end else begin
                    // No fusion - direct output
                    for (integer i = 0; i < NUM_NEURONS; i = i + 1) begin
                        neural_output[i] <= neural_layer_outputs[NUM_LAYERS-1][i];
                    end
                    
                    for (integer i = 0; i < NUM_CONCEPTS; i = i + 1) begin
                        symbolic_output[i] <= symbolic_inference_results[i];
                    end
                end
                
                processing_state <= STATE_OUTPUT;
            end
            
            STATE_OUTPUT: begin
                neural_ready <= 1;
                symbolic_ready <= 1;
                processing_complete <= 1;
                processing_state <= STATE_IDLE;
            end
            
            default: processing_state <= STATE_IDLE;
        endcase
    end
end

// Enhance symbolic reasoning with neural features
function [SYMBOLIC_WIDTH-1:0] enhance_symbolic_with_neural;
    input [SYMBOLIC_WIDTH-1:0] symbolic_tv;
    input [31:0] concept_id;
    reg [31:0] strength, confidence;
    reg [31:0] neural_influence;
    reg [31:0] enhanced_strength, enhanced_confidence;
    begin
        strength = symbolic_tv[63:32];
        confidence = symbolic_tv[31:0];
        
        // Extract neural influence (simplified)
        neural_influence = neural_layer_outputs[NUM_LAYERS-1][concept_id % NUM_NEURONS][31:0];
        
        // Neural enhancement of symbolic reasoning
        enhanced_strength = strength + (neural_influence >> 4); // Small neural contribution
        enhanced_confidence = confidence + (neural_influence >> 5);
        
        // Clamp values
        if (enhanced_strength > 32'hFFFFFFFF) enhanced_strength = 32'hFFFFFFFF;
        if (enhanced_confidence > 32'hFFFFFFFF) enhanced_confidence = 32'hFFFFFFFF;
        
        enhance_symbolic_with_neural = {enhanced_strength, enhanced_confidence};
    end
endfunction

// ============================================================================
// Performance Monitoring
// ============================================================================

always @(posedge clk) begin
    if (!rst_n) begin
        cycle_counter <= 0;
        neural_operations <= 0;
        symbolic_operations <= 0;
        last_neural_ops <= 0;
        last_symbolic_ops <= 0;
        neural_ops_per_second <= 0;
        symbolic_ops_per_second <= 0;
        fusion_efficiency <= 0;
    end else begin
        cycle_counter <= cycle_counter + 1;
        
        // Calculate operations per second (every 100M cycles at 100MHz = 1 second)
        if (cycle_counter[26:0] == 0) begin
            neural_ops_per_second <= neural_operations - last_neural_ops;
            symbolic_ops_per_second <= symbolic_operations - last_symbolic_ops;
            last_neural_ops <= neural_operations;
            last_symbolic_ops <= symbolic_operations;
            
            // Calculate fusion efficiency
            if (fusion_enable) begin
                fusion_efficiency <= ((neural_ops_per_second + symbolic_ops_per_second) * 100) / 
                                   (neural_ops_per_second + symbolic_ops_per_second + 1);
            end else begin
                fusion_efficiency <= 0;
            end
        end
    end
end

endmodule

/*
 * Neural-Symbolic Memory Controller
 * Manages memory for both neural and symbolic components
 */
module neural_symbolic_memory_controller #(
    parameter NEURAL_MEMORY_SIZE = 1048576,  // 1M neural activations
    parameter SYMBOLIC_MEMORY_SIZE = 65536,  // 64K symbolic concepts
    parameter MEMORY_WIDTH = 512
)(
    input wire clk,
    input wire rst_n,
    
    // Neural memory interface
    input wire [31:0] neural_addr,
    input wire [MEMORY_WIDTH-1:0] neural_data_in,
    output reg [MEMORY_WIDTH-1:0] neural_data_out,
    input wire neural_we,
    input wire neural_re,
    
    // Symbolic memory interface
    input wire [31:0] symbolic_addr,
    input wire [63:0] symbolic_data_in,
    output reg [63:0] symbolic_data_out,
    input wire symbolic_we,
    input wire symbolic_re,
    
    // Memory arbitration
    output reg memory_conflict,
    output reg [31:0] memory_utilization
);

// Dual-port memories
reg [MEMORY_WIDTH-1:0] neural_memory [NEURAL_MEMORY_SIZE-1:0];
reg [63:0] symbolic_memory [SYMBOLIC_MEMORY_SIZE-1:0];

// Memory access tracking
reg [31:0] neural_accesses;
reg [31:0] symbolic_accesses;
reg [31:0] total_accesses;

always @(posedge clk) begin
    if (!rst_n) begin
        neural_data_out <= 0;
        symbolic_data_out <= 0;
        memory_conflict <= 0;
        neural_accesses <= 0;
        symbolic_accesses <= 0;
        total_accesses <= 0;
    end else begin
        // Neural memory operations
        if (neural_we && neural_addr < NEURAL_MEMORY_SIZE) begin
            neural_memory[neural_addr] <= neural_data_in;
            neural_accesses <= neural_accesses + 1;
        end
        if (neural_re && neural_addr < NEURAL_MEMORY_SIZE) begin
            neural_data_out <= neural_memory[neural_addr];
            neural_accesses <= neural_accesses + 1;
        end
        
        // Symbolic memory operations
        if (symbolic_we && symbolic_addr < SYMBOLIC_MEMORY_SIZE) begin
            symbolic_memory[symbolic_addr] <= symbolic_data_in;
            symbolic_accesses <= symbolic_accesses + 1;
        end
        if (symbolic_re && symbolic_addr < SYMBOLIC_MEMORY_SIZE) begin
            symbolic_data_out <= symbolic_memory[symbolic_addr];
            symbolic_accesses <= symbolic_accesses + 1;
        end
        
        // Detect memory conflicts
        memory_conflict <= (neural_we || neural_re) && (symbolic_we || symbolic_re);
        
        // Calculate memory utilization
        total_accesses <= neural_accesses + symbolic_accesses;
        memory_utilization <= (total_accesses * 100) / (NEURAL_MEMORY_SIZE + SYMBOLIC_MEMORY_SIZE);
    end
end

endmodule