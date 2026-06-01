import { signPayload, hashToken } from '../crypto/index.es.js';
import logger from '../config/winston.es.js';

class SessionError extends Error {
    constructor(message, code = 'SESSION_ERROR') {
        super(message);
        this.name = 'SessionError';
        this.code = code;
    }
}
/** Default refresh token expiry: 7 days in milliseconds */
const DEFAULT_REFRESH_TOKEN_EXPIRY = 1000 * 60 * 60 * 24 * 7;
// Factory function that takes mongoose instance and returns the methods
function createSessionMethods(mongoose) {
    /**
     * Creates a new session for a user
     */
    async function createSession(userId, options = {}) {
        var _a;
        if (!userId) {
            throw new SessionError('User ID is required', 'INVALID_USER_ID');
        }
        const expiresIn = (_a = options.expiresIn) !== null && _a !== void 0 ? _a : DEFAULT_REFRESH_TOKEN_EXPIRY;
        try {
            const Session = mongoose.models.Session;
            const currentSession = new Session({
                user: userId,
                expiration: options.expiration || new Date(Date.now() + expiresIn),
            });
            const refreshToken = await generateRefreshToken(currentSession);
            return { session: currentSession, refreshToken };
        }
        catch (error) {
            logger.error('[createSession] Error creating session:', error);
            throw new SessionError('Failed to create session', 'CREATE_SESSION_FAILED');
        }
    }
    /**
     * Finds a session by various parameters
     */
    async function findSession(params, options = { lean: true }) {
        try {
            const Session = mongoose.models.Session;
            const query = {};
            if (!params.refreshToken && !params.userId && !params.sessionId) {
                throw new SessionError('At least one search parameter is required', 'INVALID_SEARCH_PARAMS');
            }
            if (params.refreshToken) {
                const tokenHash = await hashToken(params.refreshToken);
                query.refreshTokenHash = tokenHash;
            }
            if (params.userId) {
                query.user = params.userId;
            }
            if (params.sessionId) {
                const sessionId = typeof params.sessionId === 'object' &&
                    params.sessionId !== null &&
                    'sessionId' in params.sessionId
                    ? params.sessionId.sessionId
                    : params.sessionId;
                if (!mongoose.Types.ObjectId.isValid(sessionId)) {
                    throw new SessionError('Invalid session ID format', 'INVALID_SESSION_ID');
                }
                query._id = sessionId;
            }
            // Add expiration check to only return valid sessions
            query.expiration = { $gt: new Date() };
            const sessionQuery = Session.findOne(query);
            if (options.lean) {
                return (await sessionQuery.lean());
            }
            return await sessionQuery.exec();
        }
        catch (error) {
            logger.error('[findSession] Error finding session:', error);
            throw new SessionError('Failed to find session', 'FIND_SESSION_FAILED');
        }
    }
    /**
     * Updates session expiration
     */
    async function updateExpiration(session, newExpiration, options = {}) {
        var _a;
        const expiresIn = (_a = options.expiresIn) !== null && _a !== void 0 ? _a : DEFAULT_REFRESH_TOKEN_EXPIRY;
        try {
            const Session = mongoose.models.Session;
            const sessionDoc = typeof session === 'string' ? await Session.findById(session) : session;
            if (!sessionDoc) {
                throw new SessionError('Session not found', 'SESSION_NOT_FOUND');
            }
            sessionDoc.expiration = newExpiration || new Date(Date.now() + expiresIn);
            return await sessionDoc.save();
        }
        catch (error) {
            logger.error('[updateExpiration] Error updating session:', error);
            throw new SessionError('Failed to update session expiration', 'UPDATE_EXPIRATION_FAILED');
        }
    }
    /**
     * Deletes a session by refresh token or session ID
     */
    async function deleteSession(params) {
        try {
            const Session = mongoose.models.Session;
            if (!params.refreshToken && !params.sessionId) {
                throw new SessionError('Either refreshToken or sessionId is required', 'INVALID_DELETE_PARAMS');
            }
            const query = {};
            if (params.refreshToken) {
                query.refreshTokenHash = await hashToken(params.refreshToken);
            }
            if (params.sessionId) {
                query._id = params.sessionId;
            }
            const result = await Session.deleteOne(query);
            if (result.deletedCount === 0) {
                logger.warn('[deleteSession] No session found to delete');
            }
            return result;
        }
        catch (error) {
            logger.error('[deleteSession] Error deleting session:', error);
            throw new SessionError('Failed to delete session', 'DELETE_SESSION_FAILED');
        }
    }
    /**
     * Deletes all sessions for a user
     */
    async function deleteAllUserSessions(userId, options = {}) {
        try {
            const Session = mongoose.models.Session;
            if (!userId) {
                throw new SessionError('User ID is required', 'INVALID_USER_ID');
            }
            const userIdString = typeof userId === 'object' && userId !== null ? userId.userId : userId;
            if (!mongoose.Types.ObjectId.isValid(userIdString)) {
                throw new SessionError('Invalid user ID format', 'INVALID_USER_ID_FORMAT');
            }
            const query = { user: userIdString };
            if (options.excludeCurrentSession && options.currentSessionId) {
                query._id = { $ne: options.currentSessionId };
            }
            const result = await Session.deleteMany(query);
            if (result.deletedCount && result.deletedCount > 0) {
                logger.debug(`[deleteAllUserSessions] Deleted ${result.deletedCount} sessions for user ${userIdString}.`);
            }
            return result;
        }
        catch (error) {
            logger.error('[deleteAllUserSessions] Error deleting user sessions:', error);
            throw new SessionError('Failed to delete user sessions', 'DELETE_ALL_SESSIONS_FAILED');
        }
    }
    /**
     * Generates a refresh token for a session
     */
    async function generateRefreshToken(session) {
        if (!session || !session.user) {
            throw new SessionError('Invalid session object', 'INVALID_SESSION');
        }
        try {
            const expiresIn = session.expiration
                ? session.expiration.getTime()
                : Date.now() + DEFAULT_REFRESH_TOKEN_EXPIRY;
            if (!session.expiration) {
                session.expiration = new Date(expiresIn);
            }
            const refreshToken = await signPayload({
                payload: {
                    id: session.user,
                    sessionId: session._id,
                },
                secret: process.env.JWT_REFRESH_SECRET,
                expirationTime: Math.floor((expiresIn - Date.now()) / 1000),
            });
            session.refreshTokenHash = await hashToken(refreshToken);
            await session.save();
            return refreshToken;
        }
        catch (error) {
            logger.error('[generateRefreshToken] Error generating refresh token:', error);
            throw new SessionError('Failed to generate refresh token', 'GENERATE_TOKEN_FAILED');
        }
    }
    /**
     * Counts active sessions for a user
     */
    async function countActiveSessions(userId) {
        try {
            const Session = mongoose.models.Session;
            if (!userId) {
                throw new SessionError('User ID is required', 'INVALID_USER_ID');
            }
            return await Session.countDocuments({
                user: userId,
                expiration: { $gt: new Date() },
            });
        }
        catch (error) {
            logger.error('[countActiveSessions] Error counting active sessions:', error);
            throw new SessionError('Failed to count active sessions', 'COUNT_SESSIONS_FAILED');
        }
    }
    return {
        findSession,
        SessionError,
        deleteSession,
        createSession,
        updateExpiration,
        countActiveSessions,
        generateRefreshToken,
        deleteAllUserSessions,
    };
}

export { DEFAULT_REFRESH_TOKEN_EXPIRY, SessionError, createSessionMethods };
//# sourceMappingURL=session.es.js.map
