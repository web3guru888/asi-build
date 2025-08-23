package com.asi.asiapp.data.repository

import com.asi.asiapp.data.model.Item
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ItemRepository @Inject constructor() {
    
    fun getItems(): Flow<List<Item>> = flow {
        // TODO: Implement actual data fetching
        emit(getSampleItems())
    }
    
    private fun getSampleItems(): List<Item> {
        return listOf(
            Item(
                id = 1,
                title = "Sample title",
                description = "Sample description",
                category = "Sample category",
                timestamp = "Sample timestamp",
                imageUrl = "Sample imageUrl"
            )
        )
    }
}