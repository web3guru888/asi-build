package com.example.dogbreeds.data.local.converters

import androidx.room.TypeConverter
import com.example.dogbreeds.domain.model.Image
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

class TypeConverters {
    private val gson = Gson()

    @TypeConverter
    fun fromImage(image: Image?): String? {
        return if (image == null) null else gson.toJson(image)
    }

    @TypeConverter
    fun toImage(json: String?): Image? {
        return if (json == null || json.isEmpty()) null else try {
            val type = object : TypeToken<Image>() {}.type
            gson.fromJson(json, type)
        } catch (e: Exception) {
            null
        }
    }
}