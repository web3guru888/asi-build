package com.example.dogbreeds.data.repository

import com.example.dogbreeds.data.model.BreedResponse
import com.example.dogbreeds.data.remote.DogApiService
import com.example.dogbreeds.domain.model.Breed
import com.example.dogbreeds.util.mapToDomain
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/**
 * Repository responsible for handling data operations related to dog breeds.
 * Fetches data from the remote API and performs necessary transformations.
 */
class BreedRepository @Inject constructor(private val apiService: DogApiService) {

    /**
     * Fetches the list of dog breeds from the remote API.
     *
     * @return Result containing either a list of [Breed] on success or an error message on failure.
     */
    suspend fun getBreeds(): Result<List<Breed>> = withContext(Dispatchers.IO) {
        return@withContext try {
            val response = apiService.getBreeds()
            if (response.isSuccessful && response.body() != null) {
                val breeds = response.body()!!.map { it.mapToDomain() }
                Result.success(breeds)
            } else {
                Result.failure(Exception("Failed to load breeds: ${response.message()}"))
            }
        } catch (exception: HttpException) {
            Result.failure(Exception("Network error: ${exception.message()}"))
        } catch (exception: Exception) {
            Result.failure(Exception("Unexpected error: ${exception.message}"))
        }
    }

    /**
     * Searches for breeds by name.
     *
     * @param query The search term to filter breeds by name.
     * @return Result containing either a filtered list of [Breed] or an error.
     */
    suspend fun searchBreeds(query: String): Result<List<Breed>> = withContext(Dispatchers.IO) {
        return@withContext try {
            val response = apiService.getBreeds()
            if (response.isSuccessful && response.body() != null) {
                val filteredBreeds = response.body()!!
                    .filter { it.name.contains(query, ignoreCase = true) }
                    .map { it.mapToDomain() }
                Result.success(filteredBreeds)
            } else {
                Result.failure(Exception("Failed to search breeds: ${response.message()}"))
            }
        } catch (exception: HttpException) {
            Result.failure(Exception("Network error during search: ${exception.message()}"))
        } catch (exception: Exception) {
            Result.failure(Exception("Unexpected error during search: ${exception.message}"))
        }
    }

    /**
     * Retrieves breed details by ID.
     *
     * @param id The unique identifier of the breed.
     * @return Result containing either the [Breed] object or an error.
     */
    suspend fun getBreedById(id: Int): Result<Breed> = withContext(Dispatchers.IO) {
        return@withContext try {
            val response = apiService.getBreedById(id)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.mapToDomain())
            } else {
                Result.failure(Exception("Breed not found: ${response.message()}"))
            }
        } catch (exception: HttpException) {
            Result.failure(Exception("Network error: ${exception.message()}"))
        } catch (exception: Exception) {
            Result.failure(Exception("Unexpected error: ${exception.message}"))
        }
    }
}