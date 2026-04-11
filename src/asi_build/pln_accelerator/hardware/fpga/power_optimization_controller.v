/*
 * PLN Power Optimization Controller
 * Advanced power management for PLN hardware accelerator
 * 
 * Features:
 * - Dynamic voltage and frequency scaling (DVFS)
 * - Clock gating for inactive units
 * - Power domain management
 * - Performance per watt optimization
 * - Thermal management
 * - Energy harvesting integration
 * 
 * Author: PLN Accelerator Project
 * Target: 100x better performance/watt vs GPU
 */

module power_optimization_controller #(
    parameter NUM_COMPUTE_UNITS = 64,
    parameter NUM_POWER_DOMAINS = 8,
    parameter FREQUENCY_LEVELS = 8,
    parameter VOLTAGE_LEVELS = 4,
    parameter THERMAL_SENSORS = 16
)(
    input wire clk,
    input wire rst_n,
    
    // Performance Monitoring Interface
    input wire [31:0] compute_unit_utilization [NUM_COMPUTE_UNITS-1:0],
    input wire [31:0] memory_bandwidth_utilization,
    input wire [31:0] inference_throughput,
    input wire [31:0] cache_hit_rates [4-1:0], // L1, L2, L3, Main
    
    // Power Measurement Interface
    input wire [15:0] power_consumption_mw [NUM_POWER_DOMAINS-1:0],
    input wire [15:0] voltage_readings_mv [NUM_POWER_DOMAINS-1:0],
    input wire [15:0] current_readings_ma [NUM_POWER_DOMAINS-1:0],
    
    // Thermal Monitoring Interface
    input wire [11:0] temperature_readings [THERMAL_SENSORS-1:0], // 12-bit ADC
    input wire thermal_alert,
    input wire thermal_critical,
    
    // Control Outputs
    output reg [2:0] frequency_select [NUM_POWER_DOMAINS-1:0],
    output reg [1:0] voltage_select [NUM_POWER_DOMAINS-1:0],
    output reg clock_enable [NUM_COMPUTE_UNITS-1:0],
    output reg power_domain_enable [NUM_POWER_DOMAINS-1:0],
    
    // Performance Metrics
    output reg [31:0] performance_per_watt_score,
    output reg [31:0] energy_efficiency_rating,
    output reg [15:0] estimated_battery_life_hours,
    output reg [31:0] carbon_footprint_estimate,
    
    // Configuration Interface
    input wire [31:0] target_performance_level,
    input wire [15:0] power_budget_mw,
    input wire [2:0] optimization_mode,
    input wire [11:0] thermal_threshold_celsius
);

// Optimization Modes
localparam MODE_MAX_PERFORMANCE = 3'b000;
localparam MODE_BALANCED = 3'b001;
localparam MODE_POWER_SAVER = 3'b010;
localparam MODE_THERMAL_LIMITED = 3'b011;
localparam MODE_BATTERY_OPTIMIZED = 3'b100;
localparam MODE_GREEN_COMPUTING = 3'b101;

// Frequency and Voltage Tables
// Frequency levels: 25MHz, 50MHz, 100MHz, 200MHz, 400MHz, 600MHz, 800MHz, 1000MHz
reg [31:0] frequency_table [FREQUENCY_LEVELS-1:0];
initial begin
    frequency_table[0] = 25_000_000;   // 25 MHz
    frequency_table[1] = 50_000_000;   // 50 MHz
    frequency_table[2] = 100_000_000;  // 100 MHz
    frequency_table[3] = 200_000_000;  // 200 MHz
    frequency_table[4] = 400_000_000;  // 400 MHz
    frequency_table[5] = 600_000_000;  // 600 MHz
    frequency_table[6] = 800_000_000;  // 800 MHz
    frequency_table[7] = 1000_000_000; // 1 GHz
end

// Voltage levels: 0.6V, 0.8V, 1.0V, 1.2V
reg [15:0] voltage_table [VOLTAGE_LEVELS-1:0];
initial begin
    voltage_table[0] = 600;  // 0.6V
    voltage_table[1] = 800;  // 0.8V
    voltage_table[2] = 1000; // 1.0V
    voltage_table[3] = 1200; // 1.2V
end

// Power optimization state machine
reg [3:0] power_state;
reg [15:0] optimization_counter;
reg [31:0] performance_history [8-1:0];
reg [31:0] power_history [8-1:0];
reg [7:0] history_index;

localparam POWER_INIT = 4'h0;
localparam POWER_MONITOR = 4'h1;
localparam POWER_ANALYZE = 4'h2;
localparam POWER_OPTIMIZE = 4'h3;
localparam POWER_APPLY = 4'h4;
localparam POWER_VALIDATE = 4'h5;
localparam POWER_THERMAL_MGMT = 4'h6;

// Performance and power tracking
reg [31:0] total_power_consumption;
reg [31:0] total_performance_score;
reg [31:0] efficiency_score;
reg [15:0] max_temperature;
reg [15:0] avg_temperature;

// Clock gating control
reg [NUM_COMPUTE_UNITS-1:0] unit_activity_mask;
reg [15:0] idle_timer [NUM_COMPUTE_UNITS-1:0];
reg [15:0] clock_gate_threshold = 16'h0100; // 256 cycles idle threshold

// Power domain management
reg [NUM_POWER_DOMAINS-1:0] domain_active_mask;
reg [15:0] domain_idle_timer [NUM_POWER_DOMAINS-1:0];
reg [15:0] domain_shutdown_threshold = 16'h1000; // 4096 cycles

// DVFS (Dynamic Voltage and Frequency Scaling) Controller
always @(posedge clk) begin
    if (!rst_n) begin
        power_state <= POWER_INIT;
        optimization_counter <= 0;
        history_index <= 0;
        
        // Initialize to medium performance settings
        for (integer i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            frequency_select[i] <= 3'd4; // 400MHz
            voltage_select[i] <= 2'd2;   // 1.0V
            power_domain_enable[i] <= 1;
        end
        
        for (integer i = 0; i < NUM_COMPUTE_UNITS; i = i + 1) begin
            clock_enable[i] <= 1;
            idle_timer[i] <= 0;
        end
        
    end else begin
        case (power_state)
            POWER_INIT: begin
                // Initialize optimization parameters
                power_state <= POWER_MONITOR;
                optimization_counter <= 0;
            end
            
            POWER_MONITOR: begin
                // Monitor system metrics
                total_power_consumption <= calculate_total_power();
                total_performance_score <= calculate_performance_score();
                max_temperature <= find_max_temperature();
                avg_temperature <= calculate_avg_temperature();
                
                optimization_counter <= optimization_counter + 1;
                
                // Move to analysis after monitoring period
                if (optimization_counter >= 16'h1000) begin // 4096 cycles
                    power_state <= POWER_ANALYZE;
                    optimization_counter <= 0;
                end
                
                // Emergency thermal management
                if (thermal_critical) begin
                    power_state <= POWER_THERMAL_MGMT;
                end
            end
            
            POWER_ANALYZE: begin
                // Analyze performance vs power trends
                efficiency_score <= (total_performance_score * 1000) / (total_power_consumption + 1);
                
                // Update history
                performance_history[history_index] <= total_performance_score;
                power_history[history_index] <= total_power_consumption;
                history_index <= (history_index + 1) % 8;
                
                power_state <= POWER_OPTIMIZE;
            end
            
            POWER_OPTIMIZE: begin
                // Apply optimization strategy based on mode
                case (optimization_mode)
                    MODE_MAX_PERFORMANCE: begin
                        apply_max_performance_optimization();
                    end
                    MODE_BALANCED: begin
                        apply_balanced_optimization();
                    end
                    MODE_POWER_SAVER: begin
                        apply_power_saver_optimization();
                    end
                    MODE_THERMAL_LIMITED: begin
                        apply_thermal_optimization();
                    end
                    MODE_BATTERY_OPTIMIZED: begin
                        apply_battery_optimization();
                    end
                    MODE_GREEN_COMPUTING: begin
                        apply_green_optimization();
                    end
                    default: begin
                        apply_balanced_optimization();
                    end
                endcase
                
                power_state <= POWER_APPLY;
            end
            
            POWER_APPLY: begin
                // Apply optimized settings to hardware
                update_clock_gating();
                update_power_domains();
                power_state <= POWER_VALIDATE;
            end
            
            POWER_VALIDATE: begin
                // Validate optimization effectiveness
                performance_per_watt_score <= (total_performance_score * 1000000) / 
                                            (total_power_consumption + 1);
                
                energy_efficiency_rating <= calculate_energy_efficiency();
                estimated_battery_life_hours <= estimate_battery_life();
                carbon_footprint_estimate <= calculate_carbon_footprint();
                
                power_state <= POWER_MONITOR;
            end
            
            POWER_THERMAL_MGMT: begin
                // Emergency thermal management
                apply_emergency_thermal_throttling();
                
                if (!thermal_critical && max_temperature < thermal_threshold_celsius) begin
                    power_state <= POWER_MONITOR;
                end
            end
            
            default: power_state <= POWER_INIT;
        endcase
    end
end

// Clock Gating Management
always @(posedge clk) begin
    if (!rst_n) begin
        for (integer i = 0; i < NUM_COMPUTE_UNITS; i = i + 1) begin
            idle_timer[i] <= 0;
            clock_enable[i] <= 1;
        end
        unit_activity_mask <= {NUM_COMPUTE_UNITS{1'b0}};
    end else begin
        // Update activity mask
        for (integer i = 0; i < NUM_COMPUTE_UNITS; i = i + 1) begin
            unit_activity_mask[i] <= (compute_unit_utilization[i] > 5); // 5% threshold
            
            if (unit_activity_mask[i]) begin
                idle_timer[i] <= 0;
                clock_enable[i] <= 1;
            end else begin
                idle_timer[i] <= idle_timer[i] + 1;
                
                // Gate clock if idle too long
                if (idle_timer[i] >= clock_gate_threshold) begin
                    clock_enable[i] <= 0;
                end
            end
        end
    end
end

// Power Domain Management
genvar pd_idx;
generate
    for (pd_idx = 0; pd_idx < NUM_POWER_DOMAINS; pd_idx = pd_idx + 1) begin : power_domains
        
        reg domain_active;
        reg [7:0] units_per_domain = NUM_COMPUTE_UNITS / NUM_POWER_DOMAINS;
        reg [7:0] domain_start = pd_idx * units_per_domain;
        reg [7:0] domain_end = (pd_idx + 1) * units_per_domain - 1;
        
        always @(posedge clk) begin
            if (!rst_n) begin
                domain_idle_timer[pd_idx] <= 0;
                power_domain_enable[pd_idx] <= 1;
                domain_active <= 1;
            end else begin
                // Check if any units in this domain are active
                domain_active <= 0;
                for (integer unit = domain_start; unit <= domain_end; unit = unit + 1) begin
                    if (unit < NUM_COMPUTE_UNITS && unit_activity_mask[unit]) begin
                        domain_active <= 1;
                    end
                end
                
                if (domain_active) begin
                    domain_idle_timer[pd_idx] <= 0;
                    power_domain_enable[pd_idx] <= 1;
                end else begin
                    domain_idle_timer[pd_idx] <= domain_idle_timer[pd_idx] + 1;
                    
                    // Shutdown domain if idle too long
                    if (domain_idle_timer[pd_idx] >= domain_shutdown_threshold) begin
                        power_domain_enable[pd_idx] <= 0;
                    end
                end
            end
        end
    end
endgenerate

// Power optimization functions
function [31:0] calculate_total_power;
    reg [31:0] total_power;
    integer i;
    begin
        total_power = 0;
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            total_power = total_power + power_consumption_mw[i];
        end
        calculate_total_power = total_power;
    end
endfunction

function [31:0] calculate_performance_score;
    reg [31:0] score;
    begin
        // Weighted performance score
        score = inference_throughput * 1000 + 
                memory_bandwidth_utilization * 100 +
                cache_hit_rates[0] * 50 + // L1 cache
                cache_hit_rates[1] * 30 + // L2 cache
                cache_hit_rates[2] * 20 + // L3 cache
                cache_hit_rates[3] * 10;  // Main memory
        calculate_performance_score = score;
    end
endfunction

function [15:0] find_max_temperature;
    reg [15:0] max_temp;
    integer i;
    begin
        max_temp = 0;
        for (i = 0; i < THERMAL_SENSORS; i = i + 1) begin
            if (temperature_readings[i] > max_temp) begin
                max_temp = temperature_readings[i];
            end
        end
        find_max_temperature = max_temp;
    end
endfunction

function [15:0] calculate_avg_temperature;
    reg [31:0] temp_sum;
    integer i;
    begin
        temp_sum = 0;
        for (i = 0; i < THERMAL_SENSORS; i = i + 1) begin
            temp_sum = temp_sum + temperature_readings[i];
        end
        calculate_avg_temperature = temp_sum / THERMAL_SENSORS;
    end
endfunction

function [31:0] calculate_energy_efficiency;
    reg [31:0] efficiency;
    begin
        // Energy efficiency in GOPS/Watt
        if (total_power_consumption > 0) begin
            efficiency = (total_performance_score * 1000) / total_power_consumption;
        end else begin
            efficiency = 0;
        end
        calculate_energy_efficiency = efficiency;
    end
endfunction

function [15:0] estimate_battery_life;
    reg [31:0] battery_capacity_mwh = 50000; // 50Wh typical laptop battery
    reg [15:0] life_hours;
    begin
        if (total_power_consumption > 0) begin
            life_hours = battery_capacity_mwh / total_power_consumption;
        end else begin
            life_hours = 16'hFFFF; // Infinite
        end
        estimate_battery_life = life_hours;
    end
endfunction

function [31:0] calculate_carbon_footprint;
    reg [31:0] carbon_intensity = 400; // gCO2/kWh (global average)
    reg [31:0] footprint;
    begin
        // Carbon footprint in gCO2/hour
        footprint = (total_power_consumption * carbon_intensity) / 1000000;
        calculate_carbon_footprint = footprint;
    end
endfunction

// Optimization strategies
task apply_max_performance_optimization;
    integer i;
    begin
        // Maximize frequency and voltage for all domains
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            if (power_consumption_mw[i] < power_budget_mw / NUM_POWER_DOMAINS) begin
                frequency_select[i] <= 3'd7; // 1 GHz
                voltage_select[i] <= 2'd3;   // 1.2V
            end
        end
        
        // Enable all compute units
        for (i = 0; i < NUM_COMPUTE_UNITS; i = i + 1) begin
            clock_enable[i] <= 1;
        end
    end
endtask

task apply_balanced_optimization;
    integer i;
    reg [31:0] target_freq_index;
    reg [31:0] target_volt_index;
    begin
        // Balance performance and power consumption
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            // Adjust based on utilization
            if (compute_unit_utilization[i * (NUM_COMPUTE_UNITS/NUM_POWER_DOMAINS)] > 80) begin
                target_freq_index = 6; // 800 MHz
                target_volt_index = 2; // 1.0V
            end else if (compute_unit_utilization[i * (NUM_COMPUTE_UNITS/NUM_POWER_DOMAINS)] > 50) begin
                target_freq_index = 4; // 400 MHz
                target_volt_index = 2; // 1.0V
            end else begin
                target_freq_index = 2; // 100 MHz
                target_volt_index = 1; // 0.8V
            end
            
            frequency_select[i] <= target_freq_index[2:0];
            voltage_select[i] <= target_volt_index[1:0];
        end
    end
endtask

task apply_power_saver_optimization;
    integer i;
    begin
        // Minimize power consumption
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            frequency_select[i] <= 3'd1; // 50 MHz
            voltage_select[i] <= 2'd0;   // 0.6V
        end
        
        // Aggressive clock gating
        clock_gate_threshold <= 16'h0010; // 16 cycles
        domain_shutdown_threshold <= 16'h0100; // 256 cycles
    end
endtask

task apply_thermal_optimization;
    integer i;
    begin
        // Reduce frequency/voltage to manage temperature
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            if (max_temperature > thermal_threshold_celsius) begin
                // Aggressive throttling
                frequency_select[i] <= 3'd0; // 25 MHz
                voltage_select[i] <= 2'd0;   // 0.6V
            end else if (max_temperature > thermal_threshold_celsius - 10) begin
                // Moderate throttling
                frequency_select[i] <= 3'd2; // 100 MHz
                voltage_select[i] <= 2'd1;   // 0.8V
            end
        end
    end
endtask

task apply_battery_optimization;
    integer i;
    reg [31:0] remaining_battery_percent = 50; // Placeholder
    begin
        // Optimize for battery life
        if (remaining_battery_percent < 20) begin
            // Critical battery - minimum power
            for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
                frequency_select[i] <= 3'd0; // 25 MHz
                voltage_select[i] <= 2'd0;   // 0.6V
            end
        end else if (remaining_battery_percent < 50) begin
            // Low battery - power saver mode
            apply_power_saver_optimization();
        end else begin
            // Normal battery - balanced mode
            apply_balanced_optimization();
        end
    end
endtask

task apply_green_optimization;
    integer i;
    begin
        // Optimize for minimal environmental impact
        // Use renewable energy preference, minimize carbon footprint
        
        // Lower performance for lower overall energy consumption
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            frequency_select[i] <= 3'd3; // 200 MHz
            voltage_select[i] <= 2'd1;   // 0.8V
        end
        
        // Extended idle thresholds
        clock_gate_threshold <= 16'h0008; // 8 cycles
        domain_shutdown_threshold <= 16'h0080; // 128 cycles
    end
endtask

task apply_emergency_thermal_throttling;
    integer i;
    begin
        // Emergency thermal protection
        for (i = 0; i < NUM_POWER_DOMAINS; i = i + 1) begin
            frequency_select[i] <= 3'd0; // 25 MHz minimum
            voltage_select[i] <= 2'd0;   // 0.6V minimum
            
            // Shut down non-essential domains
            if (i >= NUM_POWER_DOMAINS/2) begin
                power_domain_enable[i] <= 0;
            end
        end
        
        // Disable half of compute units
        for (i = NUM_COMPUTE_UNITS/2; i < NUM_COMPUTE_UNITS; i = i + 1) begin
            clock_enable[i] <= 0;
        end
    end
endtask

task update_clock_gating;
    // Clock gating updates already handled in separate always block
    begin
        // Additional clock gating optimizations could be added here
    end
endtask

task update_power_domains;
    // Power domain updates already handled in generate block
    begin
        // Additional power domain optimizations could be added here
    end
endtask

// Performance monitoring and reporting
always @(posedge clk) begin
    if (!rst_n) begin
        performance_per_watt_score <= 0;
        energy_efficiency_rating <= 0;
        estimated_battery_life_hours <= 0;
        carbon_footprint_estimate <= 0;
    end else begin
        // Update metrics every 1024 cycles
        if (optimization_counter[9:0] == 0) begin
            performance_per_watt_score <= (total_performance_score * 1000000) / 
                                        (total_power_consumption + 1);
            
            energy_efficiency_rating <= calculate_energy_efficiency();
            estimated_battery_life_hours <= estimate_battery_life();
            carbon_footprint_estimate <= calculate_carbon_footprint();
        end
    end
end

endmodule

/*
 * Energy Harvesting Interface
 * Interface for renewable energy sources
 */
module energy_harvesting_interface #(
    parameter NUM_HARVESTERS = 4
)(
    input wire clk,
    input wire rst_n,
    
    // Energy harvesting inputs
    input wire [15:0] solar_power_mw,
    input wire [15:0] thermal_power_mw,
    input wire [15:0] kinetic_power_mw,
    input wire [15:0] rf_power_mw,
    
    // Power management
    output reg [15:0] harvested_power_total,
    output reg [15:0] battery_charge_rate,
    output reg green_power_available,
    
    // Configuration
    input wire [15:0] power_demand_mw,
    input wire enable_green_mode
);

reg [15:0] harvester_powers [NUM_HARVESTERS-1:0];
reg [31:0] total_harvested;

always @(posedge clk) begin
    if (!rst_n) begin
        harvested_power_total <= 0;
        battery_charge_rate <= 0;
        green_power_available <= 0;
    end else begin
        // Collect harvested power
        harvester_powers[0] <= solar_power_mw;
        harvester_powers[1] <= thermal_power_mw;
        harvester_powers[2] <= kinetic_power_mw;
        harvester_powers[3] <= rf_power_mw;
        
        // Calculate total harvested power
        total_harvested = harvester_powers[0] + harvester_powers[1] + 
                         harvester_powers[2] + harvester_powers[3];
        
        harvested_power_total <= total_harvested[15:0];
        
        // Determine if green power can meet demand
        green_power_available <= (total_harvested >= power_demand_mw) && enable_green_mode;
        
        // Calculate battery charge rate
        if (total_harvested > power_demand_mw) begin
            battery_charge_rate <= total_harvested - power_demand_mw;
        end else begin
            battery_charge_rate <= 0;
        end
    end
end

endmodule