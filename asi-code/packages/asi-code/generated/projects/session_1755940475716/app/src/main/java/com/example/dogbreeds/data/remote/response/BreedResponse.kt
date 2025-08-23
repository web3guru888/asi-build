package com.example.dogbreeds.data.remote.response

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BreedResponse(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "bred_for") val bredFor: String?,
    @Json(name = "breed_group") val breedGroup: String?,
    @Json(name = "life_span") val lifeSpan: String?,
    @Json(name = "temperament") val temperament: String?,
    @Json(name = "origin") val origin: String?,
    @Json(name = "reference_image_id") val referenceImageId: String?,
    @Json(name = "image") val image: ImageResponse?
)

@JsonClass(generateAdapter = true)
data class ImageResponse(
    @Json(name = "url") val url: String,
    @Json(name = "width") val width: Int,
    @Json(name = "height") val height: Int
)