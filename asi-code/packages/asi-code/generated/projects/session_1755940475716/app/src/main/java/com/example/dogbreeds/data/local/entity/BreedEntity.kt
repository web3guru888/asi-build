package com.example.dogbreeds.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Entity class representing a dog breed in the local database.
 * This class is used by Room persistence library to map data to the underlying SQLite table.
 *
 * @property id The unique identifier for the breed (served as primary key)
 * @property name The name of the dog breed
 * @property origin The country or region where the breed originated
 * @property temperament Common personality traits of the breed
 * @property lifeSpan Estimated lifespan of the breed in years
 * @property imageUrl URL to an image representing the breed (optional)
 * @property subBreed List of sub-breeds (if any), stored as comma-separated string
 */
@Entity(tableName = "breed_table")
data class BreedEntity(
    @PrimaryKey val id: String,
    val name: String,
    val origin: String? = null,
    val temperament: String? = null,
    val lifeSpan: String? = null,
    val imageUrl: String? = null,
    val subBreed: String? = null
)

/**
 * Utility extension function to convert BreedEntity to domain model Breed
 */
fun BreedEntity.toDomainModel(): com.example.dogbreeds.domain.model.Breed {
    return com.example.dogbreeds.domain.model.Breed(
        id = this.id,
        name = this.name,
        origin = this.origin,
        temperament = this.temperament,
        lifeSpan = this.lifeSpan,
        imageUrl = this.imageUrl,
        subBreed = this.subBreed?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() } ?: emptyList()
    )
}