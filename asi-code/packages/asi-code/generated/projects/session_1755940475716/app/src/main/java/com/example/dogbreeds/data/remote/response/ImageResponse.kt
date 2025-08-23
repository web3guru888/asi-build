package com.example.dogbreeds.data.remote.response

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ImageResponse(
    @Json(name = "id") val id: String,
    @Json(name = "url") val url: String,
    @Json(name = "width") val width: Int,
    @Json(name = "height") val height: Int,
    @Json(name = "breeds") val breeds: List<BreedResponse> = emptyList()
) {
    companion object {
        // Placeholder image URL for breeds that don't have associated images
        const val PLACEHOLDER_IMAGE_URL = "https://placehold.co/600x400?text=No+Image+Available"
    }

    // Convenience property to get the first breed associated with the image, if any
    val breed: BreedResponse?
        get() = breeds.firstOrNull()
}