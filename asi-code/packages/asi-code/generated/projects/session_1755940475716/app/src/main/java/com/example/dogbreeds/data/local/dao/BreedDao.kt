package com.example.dogbreeds.data.local.dao

import androidx.room.*
import com.example.dogbreeds.data.local.entity.BreedEntity
import kotlinx.coroutines.flow.Flow

/**
 * Data Access Object for accessing breed-related data in the local database.
 * Provides methods to insert, query, update, and delete breed entities.
 */
@Dao
interface BreedDao {

    /**
     * Retrieves all breeds from the database as a cold [Flow].
     * The flow will emit a new list whenever the data in the database changes.
     *
     * @return Flow of list of [BreedEntity]
     */
    @Query("SELECT * FROM breed_table ORDER BY name ASC")
    fun getAllBreeds(): Flow<List<BreedEntity>>

    /**
     * Retrieves a specific breed by its ID.
     *
     * @param id The unique identifier of the breed
     * @return Flow of nullable [BreedEntity], emits null if not found
     */
    @Query("SELECT * FROM breed_table WHERE id = :id")
    fun getBreedById(id: String): Flow<BreedEntity?>

    /**
     * Searches for breeds whose name contains the given query string (case-insensitive).
     *
     * @param query Search keyword to match against breed names
     * @return Flow of list of [BreedEntity] matching the search term
     */
    @Query("SELECT * FROM breed_table WHERE name LIKE '%' || :query || '%' ORDER BY name ASC")
    fun searchBreeds(query: String): Flow<List<BreedEntity>>

    /**
     * Inserts a single breed entity into the database.
     * If the breed already exists (based on primary key), it will be replaced.
     *
     * @param breedEntity The [BreedEntity] to insert
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBreed(breedEntity: BreedEntity)

    /**
     * Inserts multiple breed entities into the database in a single transaction.
     * Existing entries will be replaced if there's a conflict.
     *
     * @param breedEntities List of [BreedEntity] to insert
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBreeds(breedEntities: List<BreedEntity>)

    /**
     * Updates an existing breed entity in the database.
     *
     * @param breedEntity The [BreedEntity] with updated values
     * @return The number of rows updated (should be 1 if successful)
     */
    @Update
    suspend fun updateBreed(breedEntity: BreedEntity): Int

    /**
     * Deletes a specific breed from the database.
     *
     * @param breedEntity The [BreedEntity] to delete
     * @return The number of rows deleted (should be 1 if successful)
     */
    @Delete
    suspend fun deleteBreed(breedEntity: BreedEntity): Int

    /**
     * Deletes all breeds from the database.
     * Useful when refreshing data to prevent duplicates.
     */
    @Query("DELETE FROM breed_table")
    suspend fun deleteAllBreeds()
}