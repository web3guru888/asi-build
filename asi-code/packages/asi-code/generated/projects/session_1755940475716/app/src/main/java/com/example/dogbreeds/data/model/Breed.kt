package com.example.dogbreeds.data.model

import com.squareup.moshi.Json

data class Breed(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "bred_for") val bredFor: String?,
    @Json(name = "breed_group") val breedGroup: String?,
    @Json(name = "life_span") val lifeSpan: String?,
    @Json(name = "temperament") val temperament: String?,
    @Json(name = "origin") val origin: String?,
    @Json(name = "reference_image_id") val referenceImageId: String?,
    @Json(name = "image") val image: ImageInfo?
)

data class ImageInfo(
    @Json(name = "url") val url: String,
    @Json(name = "width") val width: Int?,
    @Json(name = "height") val height: Int?
)