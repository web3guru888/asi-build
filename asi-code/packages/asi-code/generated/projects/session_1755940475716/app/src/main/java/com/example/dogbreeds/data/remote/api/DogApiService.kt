package com.example.dogbreeds.data.remote.api

import com.example.dogbreeds.data.model.BreedResponse
import com.example.dogbreeds.data.model.ImageResponse
import retrofit2.Response
import retrofit2.http.GET
import retrofit2.http.Headers
import retrofit2.http.Query

/**
 * Retrofit API service interface for interacting with The Dog API.
 * Defines methods to fetch dog breeds and related images.
 */
interface DogApiService {

    /**
     * Fetches a list of all dog breeds with basic information.
     * This endpoint returns paginated results; default page size is determined by the API.
     *
     * @return Response containing a list of breed data
     */
    @Headers("Content-Type: application/json")
    @GET("v1/breeds")
    suspend fun getAllBreeds(): Response<List<BreedResponse>>

    /**
     * Searches for breeds by name. Performs a case-insensitive search.
     *
     * @param query Search term for breed name
     * @return Response containing a list of matching breeds
     */
    @Headers("Content-Type: application/json")
    @GET("v1/breeds/search")
    suspend fun searchBreeds(@Query("q") query: String): Response<List<BreedResponse>>

    /**
     * Fetches a random dog image. Can be used for placeholders or featured images.
     *
     * @return Response containing image data including URL and associated breed (if any)
     */
    @Headers("Content-Type: application/json")
    @GET("v1/images/search")
    suspend fun getRandomImage(): Response<List<ImageResponse>>

    /**
     * Fetches images for a specific breed using breed ID.
     *
     * @param breedId ID of the breed to fetch images for
     * @param limit Maximum number of images to return
     * @return Response containing a list of image data for the breed
     */
    @Headers("Content-Type: application/json")
    @GET("v1/images/search")
    suspend fun getImagesByBreed(
        @Query("breed_id") breedId: Int,
        @Query("limit") limit: Int = 10
    ): Response<List<ImageResponse]>
}