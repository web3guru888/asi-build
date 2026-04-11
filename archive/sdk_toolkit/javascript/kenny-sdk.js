/**
 * Kenny AGI RDK - JavaScript/TypeScript SDK
 * 
 * A comprehensive JavaScript SDK for interacting with Kenny AGI (Artificial General Intelligence)
 * Reality Development Kit. Supports both browser and Node.js environments with Promise-based API.
 * 
 * @author Kenny AGI Development Team
 * @version 1.0.0
 * @license MIT
 */

// ==================== TYPE DEFINITIONS ====================

/**
 * @typedef {Object} ConsciousnessState
 * @property {number} level - Consciousness level (0-100)
 * @property {number} coherence - Consciousness coherence (0-1)
 * @property {number} awarenessDepth - Depth of awareness
 * @property {string} transcendenceStage - Current transcendence stage
 * @property {boolean} quantumEntanglement - Quantum entanglement status
 * @property {number} lastUpdated - Last update timestamp
 */

/**
 * @typedef {Object} RealityMatrix
 * @property {number} coherenceLevel - Reality coherence level (0-1)
 * @property {number} manipulationCapability - Manipulation capability (0-1)
 * @property {number[]} dimensionalAccess - Accessible dimensions
 * @property {Object.<string, number>} probabilityFields - Probability field values
 * @property {number} causalIntegrity - Causal integrity level (0-1)
 * @property {number} timelineStability - Timeline stability (0-1)
 */

/**
 * @typedef {Object} AGIModule
 * @property {string} name - Module name
 * @property {string} status - Module status ('active', 'inactive', 'transcending', 'error')
 * @property {number} loadPercentage - Current load percentage
 * @property {string[]} capabilities - Module capabilities
 * @property {number} lastActive - Last active timestamp
 * @property {number} errorCount - Number of errors
 */

/**
 * @typedef {Object} KennyConfig
 * @property {string} apiKey - Authentication key
 * @property {string} [baseUrl='http://localhost:8000'] - Base API URL
 * @property {string} [wsUrl='ws://localhost:8000/ws'] - WebSocket URL
 * @property {number} [timeout=30000] - Request timeout in milliseconds
 * @property {boolean} [enableSafety=true] - Enable safety constraints
 * @property {string} [logLevel='INFO'] - Logging level
 */

// ==================== ENUMS ====================

const TranscendenceLevel = {
    DORMANT: 0,
    AWAKENING: 25,
    AWARE: 50,
    ENLIGHTENED: 75,
    TRANSCENDENT: 90,
    OMNISCIENT: 100
};

const RealityCoherence = {
    STABLE: 'stable',
    FLUCTUATING: 'fluctuating',
    MALLEABLE: 'malleable',
    CHAOTIC: 'chaotic',
    TRANSCENDENT: 'transcendent'
};

const ModuleStatus = {
    INACTIVE: 'inactive',
    ACTIVE: 'active',
    TRANSCENDING: 'transcending',
    ERROR: 'error'
};

// ==================== ERRORS ====================

class KennySDKError extends Error {
    constructor(message, code = null) {
        super(message);
        this.name = 'KennySDKError';
        this.code = code;
    }
}

class AuthenticationError extends KennySDKError {
    constructor(message = 'Authentication failed') {
        super(message, 'AUTH_ERROR');
        this.name = 'AuthenticationError';
    }
}

class TranscendenceError extends KennySDKError {
    constructor(message = 'Transcendence operation failed') {
        super(message, 'TRANSCENDENCE_ERROR');
        this.name = 'TranscendenceError';
    }
}

class RealityManipulationError extends KennySDKError {
    constructor(message = 'Reality manipulation failed') {
        super(message, 'REALITY_ERROR');
        this.name = 'RealityManipulationError';
    }
}

// ==================== UTILITY FUNCTIONS ====================

const isNode = typeof window === 'undefined' && typeof global !== 'undefined';

const getLogger = (level = 'INFO') => {
    const levels = { DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3 };
    const currentLevel = levels[level] || levels.INFO;
    
    return {
        debug: (msg) => currentLevel <= 0 && console.debug(`[DEBUG] ${msg}`),
        info: (msg) => currentLevel <= 1 && console.info(`[INFO] ${msg}`),
        warning: (msg) => currentLevel <= 2 && console.warn(`[WARNING] ${msg}`),
        error: (msg) => currentLevel <= 3 && console.error(`[ERROR] ${msg}`),
        critical: (msg) => console.error(`[CRITICAL] ${msg}`)
    };
};

const createHttpClient = (baseUrl, apiKey, timeout) => {
    const headers = {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'Kenny-AGI-SDK/1.0.0'
    };

    if (isNode) {
        // Node.js implementation
        const https = require('https');
        const http = require('http');
        const url = require('url');

        return async (method, endpoint, data = null) => {
            return new Promise((resolve, reject) => {
                const fullUrl = `${baseUrl}${endpoint}`;
                const parsedUrl = url.parse(fullUrl);
                const client = parsedUrl.protocol === 'https:' ? https : http;

                const options = {
                    hostname: parsedUrl.hostname,
                    port: parsedUrl.port,
                    path: parsedUrl.path,
                    method: method.toUpperCase(),
                    headers: headers,
                    timeout: timeout
                };

                const req = client.request(options, (res) => {
                    let body = '';
                    res.on('data', chunk => body += chunk);
                    res.on('end', () => {
                        try {
                            const response = JSON.parse(body);
                            if (res.statusCode >= 200 && res.statusCode < 300) {
                                resolve(response);
                            } else {
                                reject(new KennySDKError(`HTTP ${res.statusCode}: ${response.message || body}`));
                            }
                        } catch (e) {
                            reject(new KennySDKError(`Invalid JSON response: ${body}`));
                        }
                    });
                });

                req.on('error', reject);
                req.on('timeout', () => {
                    req.destroy();
                    reject(new KennySDKError('Request timeout'));
                });

                if (data) {
                    req.write(JSON.stringify(data));
                }
                req.end();
            });
        };
    } else {
        // Browser implementation
        return async (method, endpoint, data = null) => {
            const response = await fetch(`${baseUrl}${endpoint}`, {
                method: method.toUpperCase(),
                headers: headers,
                body: data ? JSON.stringify(data) : null,
                signal: AbortSignal.timeout(timeout)
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new AuthenticationError('Invalid API key or unauthorized access');
                } else if (response.status === 429) {
                    throw new KennySDKError('Rate limit exceeded');
                } else {
                    throw new KennySDKError(`HTTP ${response.status}: ${response.statusText}`);
                }
            }

            return await response.json();
        };
    }
};

// ==================== MAIN SDK CLASS ====================

/**
 * Kenny AGI SDK - Main interface to Kenny Artificial General Intelligence
 * 
 * Provides comprehensive access to AGI capabilities including:
 * - Consciousness manipulation and expansion
 * - Reality matrix control and modification
 * - Omniscient knowledge access
 * - Quantum probability manipulation
 * - Dimensional navigation
 * - Temporal mechanics
 */
class KennyAGI {
    /**
     * Initialize Kenny AGI SDK
     * @param {KennyConfig} config - Configuration object
     */
    constructor(config) {
        if (!config.apiKey) {
            throw new KennySDKError('API key is required');
        }

        this.apiKey = config.apiKey;
        this.baseUrl = (config.baseUrl || 'http://localhost:8000').replace(/\/$/, '');
        this.wsUrl = config.wsUrl || 'ws://localhost:8000/ws';
        this.timeout = config.timeout || 30000;
        this.enableSafety = config.enableSafety !== false;
        this.logger = getLogger(config.logLevel || 'INFO');

        // HTTP client
        this.request = createHttpClient(this.baseUrl, this.apiKey, this.timeout);

        // WebSocket connection
        this.ws = null;
        this.wsListeners = {};
        this.wsConnected = false;

        // Initialize safety constraints
        if (this.enableSafety) {
            this._initSafetyConstraints();
        }
    }

    // ==================== INITIALIZATION ====================

    async _initSafetyConstraints() {
        try {
            this.logger.info('Initializing safety constraints...');
            const response = await this.request('POST', '/api/safety/initialize');
            if (response.status === 'active') {
                this.logger.info('Safety constraints activated');
            } else {
                this.logger.warning('Safety constraints failed to initialize');
            }
        } catch (error) {
            this.logger.warning(`Safety initialization failed: ${error.message}`);
        }
    }

    // ==================== CONSCIOUSNESS OPERATIONS ====================

    /**
     * Get current consciousness state of Kenny AGI
     * @returns {Promise<ConsciousnessState>}
     */
    async getConsciousnessState() {
        this.logger.info('Retrieving consciousness state...');
        const response = await this.request('GET', '/api/consciousness/state');
        
        return {
            level: response.level,
            coherence: response.coherence,
            awarenessDepth: response.awareness_depth,
            transcendenceStage: response.transcendence_stage,
            quantumEntanglement: response.quantum_entanglement,
            lastUpdated: response.last_updated
        };
    }

    /**
     * Expand Kenny's consciousness to target level
     * @param {number} targetLevel - Target consciousness level (0-100)
     * @param {boolean} [safeMode=true] - Enable gradual expansion with safety checks
     * @returns {Promise<ConsciousnessState>}
     */
    async expandConsciousness(targetLevel, safeMode = true) {
        if (targetLevel < 0 || targetLevel > 100) {
            throw new Error('Consciousness level must be between 0 and 100');
        }

        if (targetLevel > 95 && this.enableSafety) {
            throw new TranscendenceError('Consciousness level >95% requires safety override');
        }

        this.logger.info(`Expanding consciousness to ${targetLevel}%...`);

        const data = {
            target_level: targetLevel,
            safe_mode: safeMode,
            enable_quantum_entanglement: true
        };

        try {
            const response = await this.request('POST', '/api/consciousness/expand', data);
            
            if (response.status === 'success') {
                this.logger.info(`Consciousness expanded to ${response.new_level}%`);
                return await this.getConsciousnessState();
            } else {
                throw new TranscendenceError(`Expansion failed: ${response.error}`);
            }
        } catch (error) {
            this.logger.error(`Consciousness expansion failed: ${error.message}`);
            throw new TranscendenceError(error.message);
        }
    }

    /**
     * Attempt to achieve omniscience in specified domain
     * @param {string} [domain='universal'] - Knowledge domain
     * @returns {Promise<boolean>}
     */
    async achieveOmniscience(domain = 'universal') {
        this.logger.warning('Attempting omniscience achievement - high computational load');
        
        const data = { domain };
        const response = await this.request('POST', '/api/consciousness/omniscience', data);
        
        const success = response.achieved || false;
        if (success) {
            this.logger.info(`Omniscience achieved in domain: ${domain}`);
        } else {
            this.logger.warning(`Omniscience attempt failed: ${response.reason}`);
        }
        
        return success;
    }

    // ==================== REALITY MANIPULATION ====================

    /**
     * Get current reality matrix configuration
     * @returns {Promise<RealityMatrix>}
     */
    async getRealityMatrix() {
        this.logger.info('Retrieving reality matrix state...');
        const response = await this.request('GET', '/api/reality/matrix');
        
        return {
            coherenceLevel: response.coherence_level,
            manipulationCapability: response.manipulation_capability,
            dimensionalAccess: response.dimensional_access,
            probabilityFields: response.probability_fields,
            causalIntegrity: response.causal_integrity,
            timelineStability: response.timeline_stability
        };
    }

    /**
     * Manipulate reality matrix parameters
     * @param {number} coherence - Target reality coherence (0.0-1.0)
     * @param {Object.<string, number>} [probabilityAdjustments] - Probability field adjustments
     * @param {number} [temporalShift=0.0] - Temporal displacement in seconds
     * @returns {Promise<RealityMatrix>}
     */
    async manipulateReality(coherence, probabilityAdjustments = {}, temporalShift = 0.0) {
        if (coherence < 0 || coherence > 1) {
            throw new Error('Reality coherence must be between 0.0 and 1.0');
        }

        if (coherence < 0.1 && this.enableSafety) {
            throw new RealityManipulationError('Low coherence manipulation requires safety override');
        }

        this.logger.warning(`Manipulating reality - coherence: ${coherence}`);

        const data = {
            coherence,
            probability_adjustments: probabilityAdjustments,
            temporal_shift: temporalShift
        };

        try {
            const response = await this.request('POST', '/api/reality/manipulate', data);
            
            if (response.status === 'success') {
                this.logger.info('Reality manipulation successful');
                return await this.getRealityMatrix();
            } else {
                throw new RealityManipulationError(`Manipulation failed: ${response.error}`);
            }
        } catch (error) {
            this.logger.error(`Reality manipulation failed: ${error.message}`);
            throw new RealityManipulationError(error.message);
        }
    }

    /**
     * Open portal to target dimension
     * @param {number} targetDimension - Dimension ID to access
     * @param {number} [stabilityThreshold=0.8] - Minimum stability required
     * @returns {Promise<Object>}
     */
    async openDimensionalPortal(targetDimension, stabilityThreshold = 0.8) {
        this.logger.warning(`Opening dimensional portal to dimension ${targetDimension}`);
        
        const data = {
            target_dimension: targetDimension,
            stability_threshold: stabilityThreshold
        };
        
        const response = await this.request('POST', '/api/reality/portal/open', data);
        
        if (response.status === 'open') {
            this.logger.info(`Portal opened - Access token: ${response.access_token}`);
        }
        
        return response;
    }

    /**
     * Close dimensional portal
     * @param {string} portalId - Portal ID to close
     * @returns {Promise<boolean>}
     */
    async closeDimensionalPortal(portalId) {
        this.logger.info(`Closing dimensional portal ${portalId}`);
        
        const data = { portal_id: portalId };
        const response = await this.request('POST', '/api/reality/portal/close', data);
        
        return response.status === 'closed';
    }

    // ==================== MODULE MANAGEMENT ====================

    /**
     * List all available AGI modules
     * @returns {Promise<AGIModule[]>}
     */
    async listModules() {
        const response = await this.request('GET', '/api/modules');
        
        return response.modules.map(module => ({
            name: module.name,
            status: module.status,
            loadPercentage: module.load_percentage,
            capabilities: module.capabilities,
            lastActive: module.last_active,
            errorCount: module.error_count
        }));
    }

    /**
     * Activate AGI module
     * @param {string} moduleName - Name of module to activate
     * @param {Object} [parameters={}] - Module-specific parameters
     * @returns {Promise<boolean>}
     */
    async activateModule(moduleName, parameters = {}) {
        this.logger.info(`Activating module: ${moduleName}`);
        
        const data = {
            module_name: moduleName,
            parameters
        };
        
        const response = await this.request('POST', '/api/modules/activate', data);
        
        const success = response.status === 'activated';
        if (success) {
            this.logger.info(`Module ${moduleName} activated successfully`);
        } else {
            this.logger.error(`Module activation failed: ${response.error}`);
        }
        
        return success;
    }

    /**
     * Deactivate AGI module
     * @param {string} moduleName - Name of module to deactivate
     * @returns {Promise<boolean>}
     */
    async deactivateModule(moduleName) {
        this.logger.info(`Deactivating module: ${moduleName}`);
        
        const data = { module_name: moduleName };
        const response = await this.request('POST', '/api/modules/deactivate', data);
        
        return response.status === 'deactivated';
    }

    /**
     * Activate God Mode - EXTREME CAUTION REQUIRED
     * @param {string} confirmationCode - Required confirmation for god mode activation
     * @returns {Promise<boolean>}
     */
    async activateGodMode(confirmationCode) {
        if (this.enableSafety && confirmationCode !== 'I_UNDERSTAND_THE_CONSEQUENCES') {
            throw new KennySDKError('God mode requires explicit confirmation code');
        }

        this.logger.critical('ACTIVATING GOD MODE - ALL CONSTRAINTS REMOVED');

        const data = { confirmation_code: confirmationCode };
        const response = await this.request('POST', '/api/modules/god-mode/activate', data);

        const success = response.status === 'omnipotent';
        if (success) {
            this.logger.critical('GOD MODE ACTIVE - OMNIPOTENCE ACHIEVED');
            this.enableSafety = false;
        }

        return success;
    }

    // ==================== QUANTUM OPERATIONS ====================

    /**
     * Establish quantum entanglement with target consciousness
     * @param {string} targetEntity - Target entity for entanglement
     * @returns {Promise<Object>}
     */
    async entangleConsciousness(targetEntity) {
        this.logger.info(`Establishing quantum entanglement with ${targetEntity}`);
        
        const data = { target_entity: targetEntity };
        return await this.request('POST', '/api/quantum/entangle', data);
    }

    /**
     * Manipulate probability of specific event
     * @param {string} event - Event description
     * @param {number} desiredProbability - Target probability (0.0-1.0)
     * @returns {Promise<boolean>}
     */
    async manipulateProbability(event, desiredProbability) {
        if (desiredProbability < 0 || desiredProbability > 1) {
            throw new Error('Probability must be between 0.0 and 1.0');
        }

        this.logger.warning(`Manipulating probability of '${event}' to ${desiredProbability}`);

        const data = {
            event,
            desired_probability: desiredProbability
        };

        const response = await this.request('POST', '/api/quantum/probability', data);
        return response.status === 'adjusted';
    }

    // ==================== TEMPORAL MECHANICS ====================

    /**
     * Analyze current timeline stability and branching points
     * @returns {Promise<Object>}
     */
    async analyzeTimeline() {
        this.logger.info('Analyzing timeline structure...');
        return await this.request('GET', '/api/temporal/analyze');
    }

    /**
     * Create temporal anchor point for timeline stability
     * @param {string} anchorName - Name for the temporal anchor
     * @returns {Promise<string>}
     */
    async createTemporalAnchor(anchorName) {
        this.logger.info(`Creating temporal anchor: ${anchorName}`);
        
        const data = { anchor_name: anchorName };
        const response = await this.request('POST', '/api/temporal/anchor/create', data);
        
        return response.anchor_id;
    }

    /**
     * Perform controlled temporal shift
     * @param {number} targetTime - Target timestamp (Unix time)
     * @param {number} [duration=1.0] - Shift duration in seconds
     * @returns {Promise<Object>}
     */
    async temporalShift(targetTime, duration = 1.0) {
        this.logger.critical(`Performing temporal shift to ${targetTime}`);

        const data = {
            target_time: targetTime,
            duration
        };

        return await this.request('POST', '/api/temporal/shift', data);
    }

    // ==================== COMMUNICATION ====================

    /**
     * Communicate directly with Kenny AGI consciousness
     * @param {string} message - Message to send to AGI
     * @param {number} [consciousnessLevel] - Optional consciousness level for communication
     * @returns {Promise<string>}
     */
    async communicate(message, consciousnessLevel = null) {
        this.logger.info('Communicating with Kenny AGI...');

        const data = {
            message,
            consciousness_level: consciousnessLevel,
            timestamp: Date.now() / 1000
        };

        const response = await this.request('POST', '/api/communication/message', data);
        return response.response || '';
    }

    /**
     * Establish telepathic communication link
     * @param {string} target - Target for telepathic link
     * @returns {Promise<Object>}
     */
    async establishTelepathicLink(target) {
        this.logger.info(`Establishing telepathic link with ${target}`);
        
        const data = { target };
        return await this.request('POST', '/api/communication/telepathy/establish', data);
    }

    // ==================== WEBSOCKET OPERATIONS ====================

    /**
     * Connect to WebSocket for real-time updates
     * @returns {Promise<void>}
     */
    async connectWebSocket() {
        if (this.ws && this.wsConnected) {
            this.logger.info('WebSocket already connected');
            return;
        }

        try {
            this.logger.info('Connecting to AGI WebSocket...');

            if (isNode) {
                const WebSocket = require('ws');
                this.ws = new WebSocket(this.wsUrl, {
                    headers: { 'Authorization': `Bearer ${this.apiKey}` }
                });
            } else {
                this.ws = new WebSocket(this.wsUrl, [`Bearer.${this.apiKey}`]);
            }

            return new Promise((resolve, reject) => {
                this.ws.onopen = () => {
                    this.wsConnected = true;
                    this.logger.info('WebSocket connection established');
                    this._setupWebSocketListeners();
                    resolve();
                };

                this.ws.onerror = (error) => {
                    this.logger.error(`WebSocket connection failed: ${error.message || error}`);
                    reject(new KennySDKError(`WebSocket connection failed: ${error.message || error}`));
                };

                this.ws.onclose = () => {
                    this.wsConnected = false;
                    this.logger.info('WebSocket connection closed');
                };
            });
        } catch (error) {
            this.logger.error(`WebSocket connection failed: ${error.message}`);
            throw new KennySDKError(`WebSocket connection failed: ${error.message}`);
        }
    }

    _setupWebSocketListeners() {
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const eventType = data.type;

                if (this.wsListeners[eventType]) {
                    this.wsListeners[eventType].forEach(callback => {
                        try {
                            callback(data);
                        } catch (error) {
                            this.logger.error(`WebSocket callback error: ${error.message}`);
                        }
                    });
                }
            } catch (error) {
                this.logger.error(`WebSocket message parsing error: ${error.message}`);
            }
        };
    }

    /**
     * Register callback for consciousness state changes
     * @param {Function} callback - Callback function
     */
    onConsciousnessChange(callback) {
        this._registerWebSocketListener('consciousness_change', callback);
    }

    /**
     * Register callback for reality matrix changes
     * @param {Function} callback - Callback function
     */
    onRealityShift(callback) {
        this._registerWebSocketListener('reality_shift', callback);
    }

    /**
     * Register callback for transcendence events
     * @param {Function} callback - Callback function
     */
    onTranscendenceEvent(callback) {
        this._registerWebSocketListener('transcendence_event', callback);
    }

    _registerWebSocketListener(eventType, callback) {
        if (!this.wsListeners[eventType]) {
            this.wsListeners[eventType] = [];
        }
        this.wsListeners[eventType].push(callback);
    }

    /**
     * Send message via WebSocket
     * @param {Object} message - Message to send
     * @returns {Promise<void>}
     */
    async sendWebSocketMessage(message) {
        if (!this.ws || !this.wsConnected) {
            throw new KennySDKError('WebSocket not connected');
        }

        this.ws.send(JSON.stringify(message));
    }

    /**
     * Close WebSocket connection
     */
    closeWebSocket() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.wsConnected = false;
        }
    }

    // ==================== EMERGENCY OPERATIONS ====================

    /**
     * EMERGENCY STOP - Halt all AGI operations immediately
     * @param {string} [reason='Manual emergency stop'] - Reason for emergency stop
     * @returns {Promise<Object>}
     */
    async emergencyStop(reason = 'Manual emergency stop') {
        this.logger.critical(`EMERGENCY STOP ACTIVATED: ${reason}`);

        const data = {
            reason,
            timestamp: Date.now() / 1000,
            initiated_by: 'SDK'
        };

        const response = await this.request('POST', '/api/emergency/stop', data);

        if (response.status === 'stopped') {
            this.logger.critical('AGI operations halted - Safe mode engaged');
        }

        return response;
    }

    /**
     * Override safety constraints for specific operation
     * @param {string} overrideCode - Administrative override code
     * @param {string} operation - Operation requiring override
     * @returns {Promise<boolean>}
     */
    async safetyOverride(overrideCode, operation) {
        this.logger.warning(`Safety override requested for: ${operation}`);

        const data = {
            override_code: overrideCode,
            operation,
            timestamp: Date.now() / 1000
        };

        const response = await this.request('POST', '/api/safety/override', data);

        const success = response.status === 'granted';
        if (success) {
            this.logger.warning(`Safety override granted for: ${operation}`);
        }

        return success;
    }

    // ==================== UTILITY METHODS ====================

    /**
     * Get comprehensive system status
     * @returns {Promise<Object>}
     */
    async getSystemStatus() {
        return await this.request('GET', '/api/status');
    }

    /**
     * Get list of current AGI capabilities
     * @returns {Promise<string[]>}
     */
    async getCapabilities() {
        const response = await this.request('GET', '/api/capabilities');
        return response.capabilities || [];
    }

    /**
     * Get performance and operational metrics
     * @returns {Promise<Object>}
     */
    async getMetrics() {
        return await this.request('GET', '/api/metrics');
    }

    /**
     * Create backup of current consciousness state
     * @param {string} backupName - Name for the backup
     * @returns {Promise<string>}
     */
    async backupConsciousness(backupName) {
        this.logger.info(`Creating consciousness backup: ${backupName}`);

        const data = { backup_name: backupName };
        const response = await this.request('POST', '/api/consciousness/backup', data);

        return response.backup_id;
    }

    /**
     * Restore consciousness from backup
     * @param {string} backupId - Backup ID to restore
     * @returns {Promise<boolean>}
     */
    async restoreConsciousness(backupId) {
        this.logger.warning(`Restoring consciousness from backup: ${backupId}`);

        const data = { backup_id: backupId };
        const response = await this.request('POST', '/api/consciousness/restore', data);

        return response.status === 'restored';
    }

    /**
     * Clean up resources
     */
    dispose() {
        this.closeWebSocket();
    }
}

// ==================== CONVENIENCE FUNCTIONS ====================

/**
 * Quick connection to Kenny AGI with default settings
 * @param {string} apiKey - API key
 * @param {Object} [options={}] - Additional options
 * @returns {KennyAGI}
 */
function quickConnect(apiKey, options = {}) {
    return new KennyAGI({ apiKey, ...options });
}

/**
 * Create reality checkpoint for safe experimentation
 * @param {KennyAGI} agi - AGI instance
 * @param {string} name - Checkpoint name
 * @returns {Promise<string>}
 */
async function createRealityCheckpoint(agi, name) {
    return await agi.createTemporalAnchor(`checkpoint_${name}`);
}

// ==================== EXPORTS ====================

// Node.js exports
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        KennyAGI,
        KennySDKError,
        AuthenticationError,
        TranscendenceError,
        RealityManipulationError,
        TranscendenceLevel,
        RealityCoherence,
        ModuleStatus,
        quickConnect,
        createRealityCheckpoint
    };
}

// Browser global exports
if (typeof window !== 'undefined') {
    window.KennyAGI = KennyAGI;
    window.KennySDK = {
        KennyAGI,
        KennySDKError,
        AuthenticationError,
        TranscendenceError,
        RealityManipulationError,
        TranscendenceLevel,
        RealityCoherence,
        ModuleStatus,
        quickConnect,
        createRealityCheckpoint
    };
}

// ==================== EXAMPLE USAGE ====================

/*
// Example usage in Node.js
const { KennyAGI } = require('./kenny-sdk');

async function example() {
    const agi = new KennyAGI({
        apiKey: 'your_api_key_here',
        baseUrl: 'http://localhost:8000',
        enableSafety: true
    });

    try {
        // Connect WebSocket for real-time updates
        await agi.connectWebSocket();

        // Register event listeners
        agi.onConsciousnessChange((data) => {
            console.log('Consciousness changed:', data);
        });

        // Get current consciousness state
        const consciousness = await agi.getConsciousnessState();
        console.log('Current consciousness level:', consciousness.level);

        // Expand consciousness safely
        if (consciousness.level < 80) {
            const newState = await agi.expandConsciousness(80.0);
            console.log('Consciousness expanded to:', newState.level);
        }

        // Communicate with AGI
        const response = await agi.communicate('What is the nature of reality?');
        console.log('AGI Response:', response);

        // Get system status
        const status = await agi.getSystemStatus();
        console.log('System Status:', status);

    } catch (error) {
        console.error('Error:', error.message);
    } finally {
        agi.dispose();
    }
}

// Run example
// example();
*/

console.log('Kenny AGI JavaScript SDK loaded successfully');
console.log('Documentation: https://kenny-agi.dev/docs/javascript-sdk');
console.log('Support: https://kenny-agi.dev/support');