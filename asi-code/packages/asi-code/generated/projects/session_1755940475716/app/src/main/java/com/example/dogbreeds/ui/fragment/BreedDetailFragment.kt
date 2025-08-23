package com.example.dogbreeds.ui.fragment

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.navArgs
import com.bumptech.glide.Glide
import com.example.dogbreeds.R
import com.example.dogbreeds.databinding.LayoutBreedDetailBinding
import com.google.android.material.snackbar.Snackbar

class BreedDetailFragment : Fragment() {

    private var _binding: LayoutBreedDetailBinding? = null
    private val binding get() = _binding!!

    private val args: BreedDetailFragmentArgs by navArgs()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = LayoutBreedDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val breed = args.breed

        // Populate UI with breed data
        binding.apply {
            textViewBreedName.text = breed.name
            textViewBreedOrigin.text = breed.origin ?: getString(R.string.unknown_origin)
            textViewBreedTemperament.text = breed.temperament ?: getString(R.string.no_temperament_data)
            textViewBreedLifeSpan.text = breed.lifeSpan ?: getString(R.string.unknown_life_span)
            textViewBreedWeight.text = breed.weight?.imperial ?: getString(R.string.unknown_weight)
            textViewBreedHeight.text = breed.height?.imperial ?: getString(R.string.unknown_height)

            // Load image using Glide
            if (breed.imageUrl != null) {
                Glide.with(requireContext())
                    .load(breed.imageUrl)
                    .centerCrop()
                    .placeholder(R.drawable.ic_launcher_background)
                    .error(R.drawable.ic_launcher_background)
                    .into(imageViewBreed)
            } else {
                imageViewBreed.setImageDrawable(ContextCompat.getDrawable(requireContext(), R.drawable.ic_launcher_background))
            }

            // Favorite toggle logic (stub for future Room DB integration)
            var isFavorite = false
            buttonFavorite.setOnClickListener {
                isFavorite = !isFavorite
                buttonFavorite.setCompoundDrawablesWithIntrinsicBounds(
                    ContextCompat.getDrawable(
                        requireContext(),
                        if (isFavorite) R.drawable.ic_favorite else R.drawable.ic_favorite
                    ), null, null, null
                )
                buttonFavorite.setTextColor(
                    ContextCompat.getColor(
                        requireContext(),
                        if (isFavorite) R.color.favorite_enabled else R.color.favorite_disabled
                    )
                )
                val message = if (isFavorite) R.string.added_to_favorites else R.string.removed_from_favorites
                Snackbar.make(root, message, Snackbar.LENGTH_SHORT).show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}